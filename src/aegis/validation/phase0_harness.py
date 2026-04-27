"""Phase 0 validation harness for archetype artifact coverage."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aegis.storage.candidate_store import CandidateStore
from aegis.validation.archetypes import (
    ArchetypeFixture,
    load_phase0_archetypes,
)

_PASS_THRESHOLD = 0.95


class ValidationResult(BaseModel):
    """Result of validating a single archetype fixture."""

    model_config = ConfigDict(frozen=True)

    archetype_id: str
    archetype_name: str
    total_expected: int
    total_found: int
    coverage_pct: float
    missing_artifacts: list[str]
    passed: bool


class Phase0Harness:
    """Validates that Phase 0 ingestion captured archetype artifacts."""

    def __init__(self, store: CandidateStore) -> None:
        self._store = store

    def _artifact_exists(
        self, artifact_type: str, artifact_id: str
    ) -> bool:
        """Check if an artifact exists in the candidate store."""
        rows = self._store._conn.execute(
            "SELECT 1 FROM artifact_refs "
            "WHERE artifact_type = ? AND artifact_id = ? "
            "LIMIT 1",
            [artifact_type, artifact_id],
        ).fetchone()
        return rows is not None

    def validate_archetype(
        self, fixture: ArchetypeFixture
    ) -> ValidationResult:
        """Validate a single archetype fixture against the store."""
        expected: list[tuple[str, str]] = []
        for pmid in fixture.expected_artifacts.pmids:
            expected.append(("pmid", pmid))
        for nct_id in fixture.expected_artifacts.nct_ids:
            expected.append(("nct_id", nct_id))
        for grant_id in fixture.expected_artifacts.grant_ids:
            expected.append(("grant_id", grant_id))

        total_expected = len(expected)
        missing: list[str] = []
        found = 0

        for art_type, art_id in expected:
            if self._artifact_exists(art_type, art_id):
                found += 1
            else:
                missing.append(f"{art_type}:{art_id}")

        coverage = found / total_expected if total_expected > 0 else 1.0

        return ValidationResult(
            archetype_id=fixture.archetype_id,
            archetype_name=fixture.name,
            total_expected=total_expected,
            total_found=found,
            coverage_pct=coverage,
            missing_artifacts=missing,
            passed=coverage >= _PASS_THRESHOLD,
        )

    def validate_all(self) -> list[ValidationResult]:
        """Validate all Phase 0 in-scope archetypes."""
        fixtures = load_phase0_archetypes()
        return [self.validate_archetype(f) for f in fixtures]

    def generate_report(
        self, results: list[ValidationResult]
    ) -> str:
        """Generate a structured markdown report."""
        lines: list[str] = ["# Phase 0 Validation Report", ""]
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"## {r.archetype_name} [{status}]")
            lines.append("")
            lines.append(
                f"- Coverage: {r.total_found}/{r.total_expected} "
                f"({r.coverage_pct:.1%})"
            )
            if r.missing_artifacts:
                lines.append("- Missing artifacts:")
                for m in r.missing_artifacts:
                    lines.append(f"  - `{m}`")
            lines.append("")
        return "\n".join(lines)
