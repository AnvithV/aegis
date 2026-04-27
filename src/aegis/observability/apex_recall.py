"""Apex-list recall tracking with curated query regression tests."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import duckdb
import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS apex_recall_results (
    query_id TEXT NOT NULL,
    run_date DATE NOT NULL,
    recall DOUBLE NOT NULL,
    found_uuids TEXT NOT NULL,
    missed_uuids TEXT NOT NULL,
    top_k INTEGER NOT NULL,
    total_expected INTEGER NOT NULL,
    PRIMARY KEY (query_id, run_date)
);
"""


class ApexQuery(BaseModel):
    """A curated apex recall query definition."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    description: str
    mesh_terms: list[str]
    expected_uuids: list[str]
    top_k: int = 50


class RecallResult(BaseModel):
    """Result of computing recall for a single query."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    recall: float
    found_uuids: list[str]
    missed_uuids: list[str]
    top_k: int
    total_expected: int
    run_date: datetime.date


class WeeklyTrend(BaseModel):
    """Weekly trend comparison for a query's recall."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    current_recall: float
    previous_recall: float
    delta: float
    alert: bool


class ApexRecallTracker:
    """Track apex recall results and detect regressions."""

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_CREATE_TABLE)

    def load_apex_queries(self, yaml_path: str) -> list[ApexQuery]:
        """Load apex query definitions from a YAML file."""
        data = yaml.safe_load(Path(yaml_path).read_text())
        queries: list[ApexQuery] = []
        for q in data["queries"]:
            queries.append(ApexQuery(**q))
        return queries

    def compute_recall(
        self,
        expected_uuids: list[str],
        returned_uuids: list[str],
    ) -> tuple[float, list[str], list[str]]:
        """Compute recall as |intersection|/|expected|.

        Returns (recall, found_uuids, missed_uuids).
        Empty expected set returns recall = 1.0.
        """
        if len(expected_uuids) == 0:
            return 1.0, [], []

        expected_set = set(expected_uuids)
        returned_set = set(returned_uuids)
        found = sorted(expected_set & returned_set)
        missed = sorted(expected_set - returned_set)
        recall = len(found) / len(expected_set)
        return recall, found, missed

    def record_result(
        self,
        result: RecallResult,
    ) -> None:
        """Persist a recall result to DuckDB."""
        self._conn.execute(
            "INSERT INTO apex_recall_results "
            "(query_id, run_date, recall, found_uuids, "
            "missed_uuids, top_k, total_expected) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (query_id, run_date) DO UPDATE SET "
            "recall = excluded.recall, "
            "found_uuids = excluded.found_uuids, "
            "missed_uuids = excluded.missed_uuids, "
            "top_k = excluded.top_k, "
            "total_expected = excluded.total_expected",
            [
                result.query_id,
                result.run_date,
                result.recall,
                json.dumps(result.found_uuids),
                json.dumps(result.missed_uuids),
                result.top_k,
                result.total_expected,
            ],
        )

    def get_weekly_trend(
        self,
        query_id: str,
        current_date: datetime.date,
        previous_date: datetime.date,
    ) -> WeeklyTrend | None:
        """Compare recall between two dates for a query."""
        current_row = self._conn.execute(
            "SELECT recall FROM apex_recall_results "
            "WHERE query_id = ? AND run_date = ?",
            [query_id, current_date],
        ).fetchone()

        previous_row = self._conn.execute(
            "SELECT recall FROM apex_recall_results "
            "WHERE query_id = ? AND run_date = ?",
            [query_id, previous_date],
        ).fetchone()

        if current_row is None or previous_row is None:
            return None

        current_recall = float(current_row[0])
        previous_recall = float(previous_row[0])
        delta = current_recall - previous_recall
        alert = delta < -0.05

        return WeeklyTrend(
            query_id=query_id,
            current_recall=current_recall,
            previous_recall=previous_recall,
            delta=delta,
            alert=alert,
        )

    def check_all_trends(
        self,
        query_ids: list[str],
        current_date: datetime.date,
        previous_date: datetime.date,
    ) -> list[WeeklyTrend]:
        """Check recall trends for all given query IDs."""
        trends: list[WeeklyTrend] = []
        for qid in query_ids:
            trend = self.get_weekly_trend(
                qid, current_date, previous_date
            )
            if trend is not None:
                trends.append(trend)
        return trends

    def passes_threshold(
        self,
        query_ids: list[str],
        run_date: datetime.date,
        threshold: float = 0.80,
    ) -> bool:
        """Check if mean recall across queries meets threshold."""
        recalls: list[float] = []
        for qid in query_ids:
            row = self._conn.execute(
                "SELECT recall FROM apex_recall_results "
                "WHERE query_id = ? AND run_date = ?",
                [qid, run_date],
            ).fetchone()
            if row is not None:
                recalls.append(float(row[0]))

        if len(recalls) == 0:
            return False

        mean_recall = sum(recalls) / len(recalls)
        return mean_recall >= threshold
