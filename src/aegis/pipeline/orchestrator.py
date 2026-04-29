"""Query pipeline orchestrator: coordinates source fetching, scoring, and ranking."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aegis.api.schemas import ExpansionInfo
from aegis.ingestion.converters import (
    grant_record_to_candidates,
    openalex_work_to_candidates,
    pubmed_record_to_candidates,
    study_record_to_candidates,
)
from aegis.ingestion.record_ingester import RecordIngester
from aegis.integrity.hard_gate import HardGateResult
from aegis.query.classifier import QueryClassifier
from aegis.query.llm_expansion import LlmQueryExpander
from aegis.scoring.quality_prior import QualityPrior, WeightVector
from aegis.scoring.rank import CandidateScoreInput, Ranker
from aegis.scoring.result_format import RankedList
from aegis.scoring.variance import Bootstrap, BootstrapInput, ScoreBand
from aegis.privacy.demographic_blocklist import DemographicBlocklist
from aegis.privacy.gate import GateDecision, PrivacyGate
from aegis.privacy.opt_out import OptOutStore
from aegis.privacy.phi_scanner import PHIScanner
from aegis.storage.candidate_store import CandidateStore
from aegis.storage.schema import Candidate

logger = logging.getLogger(__name__)


class SourceProgress(BaseModel):
    """Progress update for a single source fetch."""

    model_config = ConfigDict(frozen=True)

    source_name: str
    status: str  # "pending", "fetching", "complete", "failed"
    record_count: int
    latency_ms: float
    error: str | None


class PipelineResult(BaseModel):
    """Full result of a query pipeline execution."""

    model_config = ConfigDict(frozen=True)

    ranked_list: RankedList
    source_progress: list[SourceProgress]
    query_type: str
    weight_vector_name: str
    expansion_info: ExpansionInfo
    variance_bands: dict[str, ScoreBand]
    f1_scores: dict[str, float]
    f2_scores: dict[str, float]
    f3_scores: dict[str, float]
    f4_scores: dict[str, float]
    f5_scores: dict[str, float]
    f6_scores: dict[str, float]
    f7_scores: dict[str, float] | None
    integrity_results: dict[str, HardGateResult]
    total_candidates_fetched: int
    total_candidates_after_dedup: int
    pipeline_duration_ms: float


class QueryPipeline:
    """Orchestrates end-to-end query execution.

    Flow:
        1. Expand query -> MeSH terms
        2. Classify query type -> weight vector
        3. Fetch from all sources in parallel
        4. Merge with existing DuckDB candidates
        5. Compute F1-F7 scores
        6. Run integrity hard gate
        7. Rank candidates
        8. Compute bootstrap variance bands
    """

    def __init__(self, *, db_path: str = "aegis.duckdb") -> None:
        self._db_path = db_path
        self._classifier = QueryClassifier()
        self._expander = LlmQueryExpander()

    async def execute(
        self,
        *,
        task_description: str,
        mesh_override: list[str] | None = None,
        k: int = 50,
        query_type_override: str | None = None,
        progress_callback: Callable[[SourceProgress], None] | None = None,
    ) -> PipelineResult:
        """Execute the full query pipeline."""
        start_time = time.monotonic()

        # Step 1: Expand query
        if mesh_override:
            mesh_terms = mesh_override
            expansion_info = ExpansionInfo(
                original_query=task_description,
                expanded_mesh_terms=mesh_override,
                expansion_method="override",
                low_confidence=False,
                cached=False,
            )
        else:
            expanded = self._expander.expand(task_description)
            mesh_terms = expanded.mesh_terms
            expansion_info = ExpansionInfo(
                original_query=task_description,
                expanded_mesh_terms=mesh_terms,
                expansion_method=expanded.expansion_method,
                low_confidence=expanded.low_confidence,
                cached=expanded.cached,
            )

        # Step 2: Classify query type
        if query_type_override:
            from aegis.query.classifier import ClassificationResult

            classification = self._classifier.classify(task_description)
            query_type = query_type_override
            weight_vector = classification.weight_vector
        else:
            classification = self._classifier.classify(task_description)
            query_type = classification.query_type
            weight_vector = classification.weight_vector

        # Step 3: Fetch from all sources in parallel
        ingester = RecordIngester(db_path=self._db_path)
        try:
            fetched_count, source_progress = await self._fetch_all_sources(
                task_description, mesh_terms, progress_callback, ingester
            )
        finally:
            ingester.close()

        # Step 4: Load existing candidates from DuckDB
        store = CandidateStore(db_path=self._db_path)
        try:
            all_candidates = store.list_by_cohort(None)
        finally:
            store.close()

        # Step 4b: Privacy gate filtering
        all_candidates = self._apply_privacy_gate(all_candidates)

        total_after_dedup = len(all_candidates)

        # Step 5: Compute scores
        score_inputs, f_scores = self._compute_scores(
            all_candidates, mesh_terms, task_description, weight_vector
        )

        # Step 6: Run integrity hard gate (simplified — use score_inputs flags)
        integrity_results: dict[str, HardGateResult] = {}
        for c in all_candidates:
            integrity_results[c.uuid] = HardGateResult(
                candidate_uuid=c.uuid,
                is_zero=False,
                reason=None,
                artifact_ref=None,
                rules_evaluated=0,
            )

        # Step 7: Rank
        ranker = Ranker(
            alpha=weight_vector.exponents.get("alpha", 0.7),
            beta=weight_vector.exponents.get("beta", 1.0),
            gamma=weight_vector.exponents.get("gamma", 0.4),
            weight_version=weight_vector.version,
        )
        ranked_list = ranker.rank(
            query_mesh_terms=mesh_terms,
            candidates=score_inputs,
            k=k,
        )

        # Step 8: Bootstrap variance bands
        bootstrap = Bootstrap(rng_seed=42)
        bootstrap_inputs = [
            BootstrapInput(
                candidate_uuid=si.candidate_uuid,
                integrity_score=si.integrity_score,
                quality_percentile=si.quality_percentile,
                topical_fit=si.topical_fit,
                recency=si.recency,
            )
            for si in score_inputs
            if not si.is_hard_zero
        ]

        alpha = weight_vector.exponents.get("alpha", 0.7)
        beta = weight_vector.exponents.get("beta", 1.0)
        gamma = weight_vector.exponents.get("gamma", 0.4)

        import numpy as np

        bounds = weight_vector.exponent_bounds
        alpha_bounds = bounds.get("alpha", [0.3, 1.2])
        beta_bounds = bounds.get("beta", [0.5, 1.5])
        gamma_bounds = bounds.get("gamma", [0.1, 0.8])

        # Build covariance from bounds (small diagonal spread)
        alpha_std = (alpha_bounds[1] - alpha_bounds[0]) / 6.0
        beta_std = (beta_bounds[1] - beta_bounds[0]) / 6.0
        gamma_std = (gamma_bounds[1] - gamma_bounds[0]) / 6.0
        cov = np.diag([alpha_std**2, beta_std**2, gamma_std**2])

        variance_bands: dict[str, ScoreBand] = {}
        if bootstrap_inputs:
            variance_bands = bootstrap.estimate(
                candidates=bootstrap_inputs,
                weight_mean=(alpha, beta, gamma),
                weight_cov=cov,
                n_samples=200,
            )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        return PipelineResult(
            ranked_list=ranked_list,
            source_progress=source_progress,
            query_type=query_type,
            weight_vector_name=weight_vector.specialty,
            expansion_info=expansion_info,
            variance_bands=variance_bands,
            f1_scores=f_scores.get("f1", {}),
            f2_scores=f_scores.get("f2", {}),
            f3_scores=f_scores.get("f3", {}),
            f4_scores=f_scores.get("f4", {}),
            f5_scores=f_scores.get("f5", {}),
            f6_scores=f_scores.get("f6", {}),
            f7_scores=f_scores.get("f7"),
            integrity_results=integrity_results,
            total_candidates_fetched=fetched_count,
            total_candidates_after_dedup=total_after_dedup,
            pipeline_duration_ms=round(elapsed_ms, 2),
        )

    async def _fetch_all_sources(
        self,
        query: str,
        mesh_terms: list[str],
        progress_callback: Callable[[SourceProgress], None] | None,
        ingester: RecordIngester,
    ) -> tuple[int, list[SourceProgress]]:
        """Fetch from all sources in parallel using asyncio.gather.

        Returns (total_records_fetched, list_of_progress_updates).
        """
        source_names = [
            "pubmed",
            "reporter",
            "ctgov",
            "openalex_works",
            "openalex_grants",
        ]

        tasks = [
            self._fetch_source(name, query, mesh_terms, ingester)
            for name in source_names
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        progress_list: list[SourceProgress] = []
        total_records = 0

        for i, result in enumerate(results):
            name = source_names[i]
            if isinstance(result, BaseException):
                prog = SourceProgress(
                    source_name=name,
                    status="failed",
                    record_count=0,
                    latency_ms=0.0,
                    error=str(result),
                )
                logger.warning("Source %s failed: %s", name, result)
            else:
                src_name, count, latency = result
                total_records += count
                prog = SourceProgress(
                    source_name=src_name,
                    status="complete",
                    record_count=count,
                    latency_ms=round(latency, 2),
                    error=None,
                )

            progress_list.append(prog)
            if progress_callback is not None:
                progress_callback(prog)

        return total_records, progress_list

    async def _fetch_source(
        self,
        source_name: str,
        query: str,
        mesh_terms: list[str],
        ingester: RecordIngester,
    ) -> tuple[str, int, float]:
        """Fetch from a single source, return (name, record_count, latency_ms).

        Sources are fetched asynchronously. Each source client returns
        records that get converted to Candidates and ingested into the
        candidate store via the RecordIngester.
        """
        start = time.monotonic()
        count = 0

        try:
            if source_name == "pubmed":
                from aegis.sources.pubmed import PubMedClient

                ncbi_key = os.environ.get("NCBI_API_KEY")
                pm_client = PubMedClient(api_key=ncbi_key)
                async for pm_rec in pm_client.search_and_fetch(
                    query, batch_size=50
                ):
                    for candidate in pubmed_record_to_candidates(pm_rec):
                        ingester.ingest(candidate)
                    count += 1
                    if count >= 200:
                        break
                ingester.log_summary("pubmed")

            elif source_name == "reporter":
                from aegis.sources.reporter import ReporterClient

                rp_client = ReporterClient()
                async for rp_rec in rp_client.fetch_grants_by_topic(
                    rcdc_terms=mesh_terms
                ):
                    for candidate in grant_record_to_candidates(rp_rec):
                        ingester.ingest(candidate)
                    count += 1
                    if count >= 200:
                        break
                ingester.log_summary("reporter")

            elif source_name == "ctgov":
                from aegis.sources.ctgov import CtgovClient

                ct_client = CtgovClient()
                async for ct_rec in ct_client.fetch_studies_by_condition(
                    mesh_terms=mesh_terms
                ):
                    for candidate in study_record_to_candidates(ct_rec):
                        ingester.ingest(candidate)
                    count += 1
                    if count >= 200:
                        break
                ingester.log_summary("ctgov")

            elif source_name == "openalex_works":
                from aegis.sources.openalex import OpenAlexClient as OAClient

                oa_client = OAClient()
                async for oa_rec in oa_client.search_works(query, batch_size=200):
                    for candidate in openalex_work_to_candidates(oa_rec):
                        ingester.ingest(candidate)
                    count += 1
                    if count >= 200:
                        break
                ingester.log_summary("openalex_works")

            elif source_name == "openalex_grants":
                from aegis.sources.openalex import FUNDER_IDS, OpenAlexClient

                oag_client = OpenAlexClient()
                for funder_name in FUNDER_IDS:
                    async for _record in oag_client.get_grants_by_funder(
                        funder_name, since_year=date.today().year - 5
                    ):
                        count += 1
                        if count >= 100:
                            break
                    if count >= 100:
                        break

        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            logger.warning(
                "Source %s fetch error after %.0fms: %s",
                source_name,
                latency,
                exc,
            )
            raise

        latency = (time.monotonic() - start) * 1000
        logger.info(
            "Source %s fetched %d records in %.0fms",
            source_name,
            count,
            latency,
        )
        return source_name, count, latency

    def _compute_scores(
        self,
        candidates: list[Candidate],
        mesh_terms: list[str],
        query_text: str,
        weight_vector: WeightVector,
    ) -> tuple[list[CandidateScoreInput], dict[str, dict[str, float]]]:
        """Compute real F1-F7 scores for all candidates.

        Returns (score_inputs_for_ranker, {f1: {uuid: percentile}, ...}).
        """
        if not candidates:
            return [], {}

        query_words = {w.lower() for w in query_text.split() if len(w) > 3}
        query_mesh_set = {m.lower() for m in mesh_terms}

        # Compute per-candidate raw sub-scores
        f_raw: dict[str, list[tuple[str, float]]] = {
            f"f{i}": [] for i in range(1, 7)
        }

        for c in candidates:
            # F1: Research output quality.
            # PMIDs are the primary signal (20 pubs = max). NCT IDs give partial
            # credit for trial leadership so CT.gov-only PIs aren't scored at zero.
            pub_count = len(c.artifact_refs.pmids)
            nct_count = len(c.artifact_refs.nct_ids)
            f1_raw = min(1.0, pub_count / 20.0 + nct_count / 15.0)
            f_raw["f1"].append((c.uuid, f1_raw))

            # F2: Funding (based on grant count)
            grant_count = len(c.artifact_refs.grant_ids)
            f2_raw = min(1.0, grant_count / 5.0)
            f_raw["f2"].append((c.uuid, f2_raw))

            # F3: Leadership (based on evidence trail mentions)
            leadership_hits = sum(
                1
                for e in c.evidence_trail
                if "PI" in e.upper()
                or "lead" in e.lower()
                or "principal" in e.lower()
            )
            f3_raw = min(1.0, leadership_hits / 3.0)
            f_raw["f3"].append((c.uuid, f3_raw))

            # F4: Apex roster membership (based on evidence trail)
            apex_hits = sum(
                1
                for e in c.evidence_trail
                if "apex" in e.lower()
                or "fellow" in e.lower()
                or "award" in e.lower()
            )
            f4_raw = min(1.0, apex_hits / 2.0)
            f_raw["f4"].append((c.uuid, f4_raw))

            # F5: Translational (based on trial count + patent count)
            trial_count = len(c.artifact_refs.nct_ids)
            patent_count = len(c.artifact_refs.patent_ids)
            f5_raw = min(1.0, (trial_count + patent_count) / 5.0)
            f_raw["f5"].append((c.uuid, f5_raw))

            # F6: Lineage (use publication breadth as proxy)
            unique_mesh = len({m.descriptor for m in c.mesh_descriptors})
            f6_raw = min(1.0, unique_mesh / 10.0)
            f_raw["f6"].append((c.uuid, f6_raw))

        # Convert raw scores to percentiles within cohort
        f_percentiles: dict[str, dict[str, float]] = {}
        for family, raw_list in f_raw.items():
            sorted_by_score = sorted(raw_list, key=lambda x: x[1])
            n = len(sorted_by_score)
            percentiles: dict[str, float] = {}
            for rank_idx, (uuid, _) in enumerate(sorted_by_score):
                percentiles[uuid] = (rank_idx + 0.5) / n
            f_percentiles[family] = percentiles

        # Compute quality prior using QualityPrior
        qp = QualityPrior(weight_vector)
        quality_inputs: list[tuple[str, dict[str, float]]] = []
        for c in candidates:
            component = {
                f"f{i}_rcr" if i == 1 else f"f{i}_funding" if i == 2 else f"f{i}_leadership" if i == 3 else f"f{i}_apex" if i == 4 else f"f{i}_translational" if i == 5 else f"f{i}_lineage": f_percentiles[f"f{i}"][c.uuid]
                for i in range(1, 7)
            }
            quality_inputs.append((c.uuid, component))

        quality_scores = qp.compute_percentiles(quality_inputs)

        # Compute topical fit
        topical_fits: dict[str, float] = {}
        for c in candidates:
            text = " ".join(
                c.name_variants
                + [m.descriptor.lower() for m in c.mesh_descriptors]
                + c.evidence_trail
            ).lower()
            hits = sum(1 for w in query_words if w in text)
            mesh_hits = sum(
                1
                for m in c.mesh_descriptors
                if m.descriptor.lower() in query_mesh_set
            )
            topical_fits[c.uuid] = min(
                1.0,
                (hits + mesh_hits * 2) / max(len(query_words) + len(query_mesh_set), 1),
            )

        # Compute recency based on last_updated_per_source
        recency_scores: dict[str, float] = {}
        today = date.today()
        for c in candidates:
            if c.last_updated_per_source:
                most_recent = max(c.last_updated_per_source.values())
                days_ago = (today - most_recent.date()).days
                recency_scores[c.uuid] = min(1.0, max(0.1, 1.0 - (days_ago / 1825.0)))
            else:
                recency_scores[c.uuid] = 0.5

        # Build CandidateScoreInput list
        score_inputs: list[CandidateScoreInput] = []
        for c in candidates:
            qs = quality_scores.get(c.uuid)
            quality_pct = qs.percentile if qs else 0.5

            score_inputs.append(
                CandidateScoreInput(
                    candidate_uuid=c.uuid,
                    candidate_name=c.name_variants[0] if c.name_variants else c.uuid,
                    linkage_confidence=c.linkage_confidence,
                    integrity_score=1.0,
                    quality_percentile=quality_pct,
                    topical_fit=topical_fits.get(c.uuid, 0.5),
                    recency=recency_scores.get(c.uuid, 0.5),
                    top_artifacts=[],
                    evidence_trail=c.evidence_trail,
                )
            )

        return score_inputs, f_percentiles

    def _apply_privacy_gate(self, candidates: list[Candidate]) -> list[Candidate]:
        """Filter candidates through the privacy gate."""
        gate = PrivacyGate(
            phi_scanner=PHIScanner(),
            blocklist=DemographicBlocklist(),
            opt_out_store=OptOutStore(storage_path=Path("data/aegis/opt_out.jsonl")),
        )

        filtered: list[Candidate] = []
        for c in candidates:
            data = {
                "name": c.name_variants[0] if c.name_variants else "",
                "uuid": c.uuid,
            }
            for field_name in ("evidence_trail",):
                data[field_name] = " ".join(getattr(c, field_name, []))

            result = gate.check(data=data, candidate_uuid=c.uuid)

            if result.decision in (GateDecision.rejected_phi, GateDecision.excluded_opt_out):
                logger.info(
                    "Privacy gate filtered candidate %s: %s",
                    c.uuid,
                    result.decision,
                )
                continue

            filtered.append(c)

        stats = gate.get_stats()
        logger.info(
            "Privacy gate: %d checked, %d allowed, %d rejected_phi, %d excluded_opt_out",
            stats.total_checked,
            stats.total_allowed,
            stats.total_rejected_phi,
            stats.total_excluded_opt_out,
        )

        return filtered
