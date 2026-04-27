"""Strong-key identity resolution using ORCID and eRA Commons ID."""

from __future__ import annotations

import uuid as _uuid

from pydantic import BaseModel, ConfigDict

from aegis.storage.candidate_store import CandidateStore
from aegis.storage.schema import ArtifactRefBundle, Candidate


class CandidateRef(BaseModel):
    """Reference to a resolved candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    matched_via: str
    confidence: float


# Resolution order: ORCID first, then eRA Commons.
_STRONG_KEY_ORDER: list[str] = ["orcid", "era_commons"]


class StrongKeyResolver:
    """Resolve artifacts to candidates via strong identity keys."""

    def __init__(self, store: CandidateStore) -> None:
        self._store = store

    def resolve(self, artifact: dict[str, str | None]) -> CandidateRef | None:
        """Look up by ORCID first, then eRA Commons. Return CandidateRef or None."""
        key_map: dict[str, str] = {
            "orcid": "orcid",
            "era_id": "era_commons",
        }
        for artifact_field, key_type in key_map.items():
            value = artifact.get(artifact_field)
            if value is None:
                continue
            candidate = self._store.get_by_strong_key(key_type, value)
            if candidate is not None:
                return CandidateRef(
                    candidate_uuid=candidate.uuid,
                    matched_via=key_type,
                    confidence=1.0,
                )
        return None

    def register(
        self, key_type: str, key_value: str, candidate_uuid: str
    ) -> None:
        """Add a single strong-key -> candidate mapping."""
        candidate = self._store.get_by_uuid(candidate_uuid)
        if candidate is None:
            raise ValueError(f"Candidate {candidate_uuid} not found")
        new_keys = dict(candidate.strong_keys)
        new_keys[key_type] = key_value
        updated = candidate.model_copy(update={"strong_keys": new_keys})
        self._store.upsert(updated)

    def bulk_register(
        self, mappings: list[tuple[str, str, str]]
    ) -> int:
        """Batch register strong-key mappings. Returns count of registrations."""
        count = 0
        for key_type, key_value, candidate_uuid in mappings:
            existing = self._store.get_by_strong_key(key_type, key_value)
            if existing is not None and existing.uuid == candidate_uuid:
                continue
            self.register(key_type, key_value, candidate_uuid)
            count += 1
        return count


class CandidateRegistry:
    """Manages the candidate UUID namespace with strong-key lookups."""

    def __init__(self, store: CandidateStore) -> None:
        self._store = store
        self._resolver = StrongKeyResolver(store)

    def get_or_create(
        self, strong_keys: dict[str, str], name: str
    ) -> str:
        """Return existing candidate UUID if any strong key matches, else create new."""
        # Check each strong key for an existing candidate
        for key_type, key_value in strong_keys.items():
            candidate = self._store.get_by_strong_key(key_type, key_value)
            if candidate is not None:
                # Merge any new strong keys into the existing candidate
                merged_keys = dict(candidate.strong_keys)
                changed = False
                for kt, kv in strong_keys.items():
                    if kt not in merged_keys:
                        merged_keys[kt] = kv
                        changed = True
                if changed:
                    updated = candidate.model_copy(
                        update={"strong_keys": merged_keys}
                    )
                    self._store.upsert(updated)
                return candidate.uuid

        # No match: create a new candidate
        candidate_uuid = str(_uuid.uuid4())
        candidate = Candidate(
            uuid=candidate_uuid,
            strong_keys=strong_keys,
            name_variants=[name],
            affiliations=[],
            artifact_refs=ArtifactRefBundle(
                pmids=[], nct_ids=[], grant_ids=[]
            ),
            linkage_confidence=1.0,
            evidence_trail=[],
            last_updated_per_source={},
            mesh_descriptors=[],
        )
        self._store.upsert(candidate)
        return candidate_uuid
