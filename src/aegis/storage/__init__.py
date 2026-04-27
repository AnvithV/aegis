"""Candidate schema, storage layer, and migrations."""

from aegis.storage.candidate_store import CandidateStore
from aegis.storage.clinician_index import ClinicianIndex, ClinicianLookupResult
from aegis.storage.dedup import ArtifactDeduplicator, CrossReference
from aegis.storage.indexes import IndexManager
from aegis.storage.schema import (
    AffiliationSpan,
    ArtifactRefBundle,
    Candidate,
    MeshDescriptor,
    StrongKeyType,
)

__all__ = [
    "AffiliationSpan",
    "ArtifactDeduplicator",
    "ArtifactRefBundle",
    "Candidate",
    "CandidateStore",
    "ClinicianIndex",
    "ClinicianLookupResult",
    "CrossReference",
    "IndexManager",
    "MeshDescriptor",
    "StrongKeyType",
]
