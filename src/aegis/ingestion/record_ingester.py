"""RecordIngester: merge-and-upsert layer between converters and CandidateStore."""

from __future__ import annotations

import logging

from aegis.identity.probabilistic import ProbabilisticLinker
from aegis.identity.ror import RorResolver
from aegis.storage.candidate_store import CandidateStore
from aegis.storage.schema import ArtifactRefBundle, Candidate

logger = logging.getLogger(__name__)

_MAX_EVIDENCE_ITEMS = 20
_MAX_MESH_DESCRIPTORS = 30
_MAX_NAME_VARIANTS = 10


def _merge_candidates(existing: Candidate, new: Candidate) -> Candidate:
    """Merge a new candidate record into an existing one (existing.uuid preserved)."""
    # Artifact refs: union, deduplicated
    merged_pmids = list(dict.fromkeys(existing.artifact_refs.pmids + new.artifact_refs.pmids))
    merged_ncts = list(dict.fromkeys(existing.artifact_refs.nct_ids + new.artifact_refs.nct_ids))
    merged_grants = list(
        dict.fromkeys(existing.artifact_refs.grant_ids + new.artifact_refs.grant_ids)
    )
    merged_patents = list(
        dict.fromkeys(existing.artifact_refs.patent_ids + new.artifact_refs.patent_ids)
    )

    # Name variants: union, capped
    seen_names: set[str] = set()
    merged_names: list[str] = []
    for n in existing.name_variants + new.name_variants:
        if n.lower() not in seen_names:
            seen_names.add(n.lower())
            merged_names.append(n)
    merged_names = merged_names[:_MAX_NAME_VARIANTS]

    # Evidence trail: append new items, deduplicated, capped
    existing_trail_set = set(existing.evidence_trail)
    merged_trail = list(existing.evidence_trail)
    for item in new.evidence_trail:
        if item not in existing_trail_set:
            merged_trail.append(item)
    merged_trail = merged_trail[:_MAX_EVIDENCE_ITEMS]

    # MeSH descriptors: union by descriptor string, capped
    seen_mesh: set[str] = {m.descriptor.lower() for m in existing.mesh_descriptors}
    merged_mesh = list(existing.mesh_descriptors)
    for m in new.mesh_descriptors:
        if m.descriptor.lower() not in seen_mesh:
            seen_mesh.add(m.descriptor.lower())
            merged_mesh.append(m)
    merged_mesh = merged_mesh[:_MAX_MESH_DESCRIPTORS]

    # last_updated: merge dicts, new timestamps win
    merged_updated = {**existing.last_updated_per_source, **new.last_updated_per_source}

    # Strong keys: union (new keys add to existing)
    merged_strong = {**existing.strong_keys, **new.strong_keys}

    return Candidate(
        uuid=existing.uuid,
        strong_keys=merged_strong,
        name_variants=merged_names,
        affiliations=existing.affiliations or new.affiliations,
        artifact_refs=ArtifactRefBundle(
            pmids=merged_pmids,
            nct_ids=merged_ncts,
            grant_ids=merged_grants,
            patent_ids=merged_patents,
        ),
        linkage_confidence=max(existing.linkage_confidence, new.linkage_confidence),
        evidence_trail=merged_trail,
        last_updated_per_source=merged_updated,
        mesh_descriptors=merged_mesh,
    )


class RecordIngester:
    """Ingest Candidate records into DuckDB, deduplicating by strong keys
    and probabilistic name+affiliation matching.

    Maintains an in-memory cache of (key_type, key_value) → uuid to avoid
    repeated DB lookups within a single query run.  A snapshot of existing
    candidates is loaded once at init and passed to the probabilistic linker
    so that cross-source matching does not require repeated full-table scans.
    """

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._store = CandidateStore(db_path=db_path)
        self._cache: dict[tuple[str, str], str] = {}
        self.new_count = 0
        self.merged_count = 0
        self.error_count = 0
        self.linked_count = 0

        # Load existing candidates once for probabilistic linking.
        self._snapshot: list[Candidate] = self._store.list_by_cohort(None)

        ror = RorResolver()
        self._linker = ProbabilisticLinker(store=self._store, ror_resolver=ror)

    def ingest(self, candidate: Candidate) -> bool:
        """Ingest one candidate. Returns True if new, False if merged. Never raises."""
        try:
            return self._ingest_safe(candidate)
        except Exception:
            logger.warning("Failed to ingest candidate %s", candidate.uuid, exc_info=True)
            self.error_count += 1
            return False

    def _ingest_safe(self, candidate: Candidate) -> bool:
        existing_uuid = self._find_existing(candidate)

        if existing_uuid:
            existing = self._store.get_by_uuid(existing_uuid)
            if existing:
                merged = _merge_candidates(existing, candidate)
                self._upsert_with_retry(merged)
                # Update snapshot so future probabilistic lookups see the merged record
                self._snapshot = [
                    merged if c.uuid == merged.uuid else c
                    for c in self._snapshot
                ]
                self.merged_count += 1
                return False

        # New candidate — add to snapshot for future within-session linking
        self._upsert_with_retry(candidate)
        self._update_cache(candidate)
        self._snapshot.append(candidate)
        self.new_count += 1
        return True

    def _find_existing(self, candidate: Candidate) -> str | None:
        # 1. Exact strong-key match (ORCID, ERA Commons, etc.)
        for key_type, key_value in candidate.strong_keys.items():
            cache_key = (key_type, key_value)
            if cache_key in self._cache:
                return self._cache[cache_key]
            existing = self._store.get_by_strong_key(key_type, key_value)
            if existing:
                self._update_cache(existing)
                return existing.uuid

        # 2. Probabilistic name+affiliation match against in-memory snapshot.
        #    Uses the pre-loaded snapshot to avoid repeated full-table DB scans.
        name = candidate.name_variants[0] if candidate.name_variants else ""
        if not name:
            return None

        affiliation = (
            candidate.affiliations[0].canonical_name
            if candidate.affiliations
            else ""
        )
        mesh_terms = [m.descriptor for m in candidate.mesh_descriptors]

        try:
            result = self._linker.link(
                artifact_features={
                    "name": name,
                    "name_variants": candidate.name_variants,
                    "affiliation": affiliation,
                    "mesh_terms": mesh_terms,
                },
                registry=None,  # type: ignore[arg-type]  # unused by linker
                candidates=self._snapshot,
            )
            if result.action == "auto-link" and result.candidate_uuid:
                logger.debug(
                    "Probabilistic auto-link: %s → %s (confidence=%.3f)",
                    name,
                    result.candidate_uuid,
                    result.confidence,
                )
                self.linked_count += 1
                return result.candidate_uuid
        except Exception:
            logger.debug("Probabilistic link failed for %s", name, exc_info=True)

        return None

    def _update_cache(self, candidate: Candidate) -> None:
        for key_type, key_value in candidate.strong_keys.items():
            self._cache[(key_type, key_value)] = candidate.uuid

    def _upsert_with_retry(self, candidate: Candidate, max_attempts: int = 3) -> None:
        """Retry on DuckDB write conflicts (concurrent queries)."""
        import time

        for attempt in range(max_attempts):
            try:
                self._store.upsert(candidate)
                return
            except Exception as exc:
                if attempt == max_attempts - 1:
                    raise
                logger.debug("Upsert attempt %d failed: %s — retrying", attempt + 1, exc)
                time.sleep(0.1 * (2**attempt))  # 100ms, 200ms backoff

    def close(self) -> None:
        """Release the underlying DB connection."""
        self._store.close()

    def log_summary(self, source_name: str) -> None:
        """Log an INFO-level ingestion summary for the given source."""
        logger.info(
            "Ingestion [%s]: %d new, %d merged (%d probabilistic), %d errors",
            source_name,
            self.new_count,
            self.merged_count,
            self.linked_count,
            self.error_count,
        )
