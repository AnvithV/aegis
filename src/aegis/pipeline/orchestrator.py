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
from aegis.integrity.hard_gate import HardGate, HardGateResult
from aegis.query.classifier import QueryClassifier
from aegis.query.llm_expansion import LlmQueryExpander
from aegis.scoring.quality_prior import QualityPrior, WeightVector
from aegis.scoring.rank import CandidateScoreInput, Ranker
from aegis.scoring.result_format import RankedList
from aegis.scoring.variance import Bootstrap, BootstrapInput, ScoreBand
from aegis.sources.apex_rosters import ApexRosterStore
from aegis.sources.icite import IciteClient
from aegis.sources.leie import LEIEStore
from aegis.sources.ofac_sam import OFACSAMStore
from aegis.sources.ori import ORIStore
from aegis.sources.retraction_watch import RetractionWatchStore
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

    def __init__(
        self,
        *,
        db_path: str = "aegis.duckdb",
        leie_store: LEIEStore | None = None,
        ofac_sam_store: OFACSAMStore | None = None,
        ori_store: ORIStore | None = None,
        retraction_store: RetractionWatchStore | None = None,
        apex_store: ApexRosterStore | None = None,
    ) -> None:
        self._db_path = db_path
        self._classifier = QueryClassifier()
        self._expander = LlmQueryExpander()
        self._leie_store = leie_store or LEIEStore()
        self._ofac_sam_store = ofac_sam_store or OFACSAMStore()
        self._ori_store = ori_store or ORIStore()
        self._retraction_store = retraction_store or RetractionWatchStore()
        self._apex_store = apex_store
        self._rcr_map: dict[str, float] = {}

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
            expanded = await asyncio.to_thread(self._expander.expand, task_description)
            mesh_terms = expanded.mesh_terms
            expansion_info = ExpansionInfo(
                original_query=task_description,
                expanded_mesh_terms=mesh_terms,
                expansion_method=expanded.expansion_method,
                low_confidence=expanded.low_confidence,
                cached=expanded.cached,
            )

        # Step 2: Classify query type
        classification = self._classifier.classify(task_description)
        if query_type_override:
            query_type = query_type_override
        else:
            query_type = classification.query_type
        weight_vector = classification.weight_vector

        # Step 3: Fetch from all sources in parallel
        ingester = RecordIngester(db_path=self._db_path)
        try:
            fetched_count, source_progress = await self._fetch_all_sources(
                task_description, mesh_terms, progress_callback, ingester
            )
            ingested_uuids = ingester.ingested_uuids
        finally:
            ingester.close()

        # Step 4: Scoring isolation — only score candidates from this query
        store = CandidateStore(db_path=self._db_path)
        try:
            all_candidates = [
                c for c in store.list_by_cohort(None)
                if c.uuid in ingested_uuids
            ]
        finally:
            store.close()

        # Step 4b: Privacy gate filtering
        all_candidates = self._apply_privacy_gate(all_candidates)

        total_after_dedup = len(all_candidates)

        # Step 4c: iCite enrichment — fetch RCR scores for ingested PMIDs
        self._rcr_map = {}
        pmids = [p for c in all_candidates for p in c.artifact_refs.pmids]
        if pmids:
            try:
                icite = IciteClient()
                async for rec in icite.fetch_by_pmids(pmids[:200]):
                    if rec.relative_citation_ratio is not None:
                        self._rcr_map[rec.pmid] = rec.relative_citation_ratio
                logger.info("iCite enrichment: %d RCR scores fetched", len(self._rcr_map))
            except Exception:
                logger.warning("iCite enrichment failed", exc_info=True)

        # Step 5: Compute scores
        score_inputs, f_scores = self._compute_scores(
            all_candidates, mesh_terms, task_description, weight_vector
        )

        # Step 6: Run integrity hard gate
        hard_gate = HardGate(
            leie_store=self._leie_store,
            ofac_sam_store=self._ofac_sam_store,
            ori_store=self._ori_store,
            retraction_store=self._retraction_store,
        )
        integrity_results: dict[str, HardGateResult] = {}
        query_mesh_set = {m.lower() for m in mesh_terms}
        for c in all_candidates:
            candidate_mesh = {m.descriptor.lower() for m in c.mesh_descriptors}
            gate_result = hard_gate.evaluate(
                candidate_uuid=c.uuid,
                candidate_name=c.name_variants[0] if c.name_variants else c.uuid,
                candidate_mesh=candidate_mesh,
                query_mesh=query_mesh_set,
            )
            integrity_results[c.uuid] = gate_result
            if gate_result.is_zero:
                # Mark integrity_score=0 in the score inputs
                for si in score_inputs:
                    if si.candidate_uuid == c.uuid:
                        score_inputs = [
                            CandidateScoreInput(
                                candidate_uuid=si.candidate_uuid,
                                candidate_name=si.candidate_name,
                                linkage_confidence=si.linkage_confidence,
                                integrity_score=0.0,
                                quality_percentile=si.quality_percentile,
                                topical_fit=si.topical_fit,
                                recency=si.recency,
                                top_artifacts=si.top_artifacts,
                                evidence_trail=si.evidence_trail,
                                contact_email=si.contact_email,
                            )
                            if s.candidate_uuid == c.uuid
                            else s
                            for s in score_inputs
                        ]
                        break

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
            import functools
            variance_bands = await asyncio.to_thread(
                functools.partial(
                    bootstrap.estimate,
                    candidates=bootstrap_inputs,
                    weight_mean=(alpha, beta, gamma),
                    weight_cov=cov,
                    n_samples=200,
                )
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
        ]

        progress_list: list[SourceProgress] = []
        total_records = 0

        async def _fetch_and_report(name: str) -> SourceProgress:
            try:
                src_name, count, latency = await self._fetch_source(
                    name, query, mesh_terms, ingester
                )
                prog = SourceProgress(
                    source_name=src_name,
                    status="complete",
                    record_count=count,
                    latency_ms=round(latency, 2),
                    error=None,
                )
            except Exception as exc:
                logger.warning("Source %s failed: %s", name, exc)
                prog = SourceProgress(
                    source_name=name,
                    status="failed",
                    record_count=0,
                    latency_ms=0.0,
                    error=str(exc),
                )
            # Emit immediately as this source finishes
            if progress_callback is not None:
                progress_callback(prog)
            return prog

        tasks = [
            asyncio.create_task(_fetch_and_report(name))
            for name in source_names
        ]

        for prog in await asyncio.gather(*tasks):
            progress_list.append(prog)
            if prog.record_count:
                total_records += prog.record_count

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
                    rcdc_terms=mesh_terms,
                    query_text=query,
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
                async for ct_rec in ct_client.fetch_studies_by_text(
                    query_text=query[:200]
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
            f"f{i}": [] for i in range(1, 8)
        }

        for c in candidates:
            pmids = c.artifact_refs.pmids
            nct_ids = c.artifact_refs.nct_ids
            grant_ids = c.artifact_refs.grant_ids
            patent_ids = c.artifact_refs.patent_ids

            # F1: Research output quality — use RCR if available, else pub count
            rcr_vals = [self._rcr_map[p] for p in pmids if p in self._rcr_map]
            if rcr_vals:
                f1_raw = min(1.0, sum(rcr_vals) / len(rcr_vals) / 5.0)
            else:
                f1_raw = min(1.0, len(pmids) / 20.0)
            f_raw["f1"].append((c.uuid, f1_raw))

            # F2: Funding (grant count, now includes OpenAlex international grants)
            f2_raw = min(1.0, len(grant_ids) / 5.0)
            f_raw["f2"].append((c.uuid, f2_raw))

            # F3: Leadership (count evidence_trail entries with "Principal Investigator")
            pi_hits = sum(
                1 for e in c.evidence_trail if "Principal Investigator" in e
            )
            f3_raw = min(1.0, pi_hits / 3.0)
            f_raw["f3"].append((c.uuid, f3_raw))

            # F4: Apex roster membership — use real store lookup
            name = c.name_variants[0] if c.name_variants else ""
            if self._apex_store and name and self._apex_store.lookup_by_name(name):
                f4_raw = 1.0
            else:
                f4_raw = 0.0
            f_raw["f4"].append((c.uuid, f4_raw))

            # F5: Translational (trials + patents)
            f5_raw = min(1.0, (len(nct_ids) + len(patent_ids)) / 5.0)
            f_raw["f5"].append((c.uuid, f5_raw))

            # F6: Lineage (publication breadth via unique MeSH)
            unique_mesh = len({m.descriptor for m in c.mesh_descriptors})
            f6_raw = min(1.0, unique_mesh / 10.0)
            f_raw["f6"].append((c.uuid, f6_raw))

            # F7: Clinician-specific
            k_award_count = sum(
                1 for g in grant_ids
                if g.startswith("K08") or g.startswith("K23") or g.startswith("K24")
            )
            clinical_pi = 1.0 if len(nct_ids) > 0 else 0.0
            clinical_affil = 1.0 if any(
                kw in (aff.canonical_name or "").lower()
                for aff in c.affiliations
                for kw in ("hospital", "medical center", "clinic")
            ) else 0.0
            f7_raw = min(1.0, (k_award_count / 3.0 + clinical_pi + clinical_affil) / 3.0)
            f_raw["f7"].append((c.uuid, f7_raw))

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
        _FAMILY_LABELS = {
            1: "rcr", 2: "funding", 3: "leadership", 4: "apex",
            5: "translational", 6: "lineage", 7: "clinician",
        }
        qp = QualityPrior(weight_vector)
        quality_inputs: list[tuple[str, dict[str, float]]] = []
        for c in candidates:
            component = {
                f"f{i}_{_FAMILY_LABELS[i]}": f_percentiles[f"f{i}"][c.uuid]
                for i in range(1, 8)
            }
            quality_inputs.append((c.uuid, component))

        quality_scores = qp.compute_percentiles(quality_inputs)

        # Compute topical fit — source-agnostic word-coverage score.
        # Uses query words against the full searchable text (name + MeSH + evidence).
        # Avoids the MeSH-bonus formula which systematically favoured PubMed
        # candidates (NLM-indexed MeSH) over Reporter/CT.gov (RCDC categories).
        topical_fits: dict[str, float] = {}
        n_query_words = max(len(query_words), 1)
        for c in candidates:
            text = " ".join(
                c.name_variants
                + [m.descriptor.lower() for m in c.mesh_descriptors]
                + c.evidence_trail
            ).lower()
            hits = sum(1 for w in query_words if w in text)
            topical_fits[c.uuid] = hits / n_query_words

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
                    contact_email=c.contact_email,
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
