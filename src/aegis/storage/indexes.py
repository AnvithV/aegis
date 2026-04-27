"""IndexManager: cohort-scoped index building and lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aegis.storage.candidate_store import CandidateStore


class IndexManager:
    """Build and query cohort-scoped indexes over the candidate store."""

    def __init__(self, store: CandidateStore) -> None:
        self._conn = store._conn  # noqa: SLF001

    def rebuild_mesh_index(self) -> int:
        """Drop and rebuild MeSH inverted index. Return entry count."""
        self._conn.execute("DELETE FROM mesh_candidate_index")

        candidates = self._conn.execute(
            "SELECT uuid, data FROM candidates"
        ).fetchall()

        count = 0
        for uuid, data_json in candidates:
            from aegis.storage.schema import Candidate

            c = Candidate.model_validate_json(data_json)
            for md in c.mesh_descriptors:
                self._conn.execute(
                    """
                    INSERT INTO mesh_candidate_index
                        (descriptor, qualifier, major_topic,
                         candidate_uuid)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                    """,
                    [
                        md.descriptor,
                        md.qualifier or "",
                        md.major_topic,
                        uuid,
                    ],
                )
                count += 1
        return count

    def rebuild_yearly_counts(self) -> int:
        """Drop and rebuild yearly artifact count aggregation.

        Returns the number of rows created.
        """
        self._conn.execute("DELETE FROM yearly_artifact_counts")

        candidates = self._conn.execute(
            "SELECT uuid, data FROM candidates"
        ).fetchall()

        count = 0
        for uuid, data_json in candidates:
            from aegis.storage.schema import Candidate

            c = Candidate.model_validate_json(data_json)
            yearly: dict[int, dict[str, int]] = {}

            for source, ts in c.last_updated_per_source.items():
                year = ts.year
                atype = _source_to_artifact_type(source)
                yearly.setdefault(year, {})
                yearly[year][atype] = (
                    yearly[year].get(atype, 0) + 1
                )

            for year, types in yearly.items():
                for atype, cnt in types.items():
                    self._conn.execute(
                        """
                        INSERT INTO yearly_artifact_counts
                            (candidate_uuid, year,
                             artifact_type, count)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT DO NOTHING
                        """,
                        [uuid, year, atype, cnt],
                    )
                    count += 1
        return count

    def rebuild_all(self) -> dict[str, int]:
        """Rebuild all indexes. Return counts per index."""
        return {
            "mesh_index": self.rebuild_mesh_index(),
            "yearly_counts": self.rebuild_yearly_counts(),
        }

    def lookup_by_mesh(
        self,
        descriptor: str,
        qualifier: str | None = None,
    ) -> list[str]:
        """Return candidate UUIDs matching a MeSH descriptor."""
        if qualifier is not None:
            rows = self._conn.execute(
                """
                SELECT candidate_uuid
                FROM mesh_candidate_index
                WHERE descriptor = ? AND qualifier = ?
                """,
                [descriptor, qualifier or ""],
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT candidate_uuid
                FROM mesh_candidate_index
                WHERE descriptor = ?
                """,
                [descriptor],
            ).fetchall()
        return [row[0] for row in rows]

    def get_yearly_counts(
        self, candidate_uuid: str
    ) -> dict[int, dict[str, int]]:
        """Return yearly artifact counts for a candidate."""
        rows = self._conn.execute(
            """
            SELECT year, artifact_type, count
            FROM yearly_artifact_counts
            WHERE candidate_uuid = ?
            """,
            [candidate_uuid],
        ).fetchall()
        result: dict[int, dict[str, int]] = {}
        for year, atype, cnt in rows:
            result.setdefault(int(year), {})[str(atype)] = int(cnt)
        return result


def _source_to_artifact_type(source: str) -> str:
    """Map a source name to an artifact type category."""
    mapping = {
        "pubmed": "publication",
        "clinicaltrials": "trial",
        "nih_reporter": "grant",
    }
    return mapping.get(source, "publication")
