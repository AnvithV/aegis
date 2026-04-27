"""Per-source coverage diagnostics for seed cohort quality monitoring."""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from aegis.storage import CandidateStore


class CoverageMetrics(BaseModel):
    """Frozen snapshot of cohort coverage statistics."""

    model_config = ConfigDict(frozen=True)

    total_candidates: int
    strong_key_pct: float
    probabilistic_linkage_pct: float
    per_source_pct: dict[str, float]
    thin_record_pct: float
    linkage_confidence_p5: float
    linkage_confidence_p50: float
    linkage_confidence_p95: float


class CoverageDiagnostics:
    """Compute and report per-source coverage metrics from a CandidateStore."""

    def __init__(self, store: CandidateStore) -> None:
        self._store = store

    def compute(
        self, cohort_candidates: list[str] | None = None
    ) -> CoverageMetrics:
        """Compute coverage metrics for the cohort or a subset of candidate UUIDs."""
        if cohort_candidates is not None:
            candidates = []
            for uuid in cohort_candidates:
                c = self._store.get_by_uuid(uuid)
                if c is not None:
                    candidates.append(c)
        else:
            candidates = self._store.list_by_cohort()

        total = len(candidates)
        if total == 0:
            return CoverageMetrics(
                total_candidates=0,
                strong_key_pct=0.0,
                probabilistic_linkage_pct=0.0,
                per_source_pct={},
                thin_record_pct=0.0,
                linkage_confidence_p5=0.0,
                linkage_confidence_p50=0.0,
                linkage_confidence_p95=0.0,
            )

        # Strong-key percentage: has ORCID or eRA Commons
        strong_count = sum(
            1
            for c in candidates
            if "orcid" in c.strong_keys or "era_commons" in c.strong_keys
        )
        strong_key_pct = round(100.0 * strong_count / total, 2)

        # Probabilistic linkage percentage: linkage_confidence >= 0.7
        prob_count = sum(
            1 for c in candidates if c.linkage_confidence >= 0.7
        )
        probabilistic_linkage_pct = round(100.0 * prob_count / total, 2)

        # Per-source artifact percentage
        source_counts: dict[str, int] = {
            "pubmed": 0,
            "reporter": 0,
            "ctgov": 0,
        }
        for c in candidates:
            if c.artifact_refs.pmids:
                source_counts["pubmed"] += 1
            if c.artifact_refs.grant_ids:
                source_counts["reporter"] += 1
            if c.artifact_refs.nct_ids:
                source_counts["ctgov"] += 1
        per_source_pct = {
            src: round(100.0 * cnt / total, 2)
            for src, cnt in source_counts.items()
        }

        # Thin-record percentage: fewer than 3 total artifacts
        thin_count = sum(
            1
            for c in candidates
            if (
                len(c.artifact_refs.pmids)
                + len(c.artifact_refs.nct_ids)
                + len(c.artifact_refs.grant_ids)
            )
            < 3
        )
        thin_record_pct = round(100.0 * thin_count / total, 2)

        # Linkage confidence percentiles
        confidences = sorted(c.linkage_confidence for c in candidates)
        if len(confidences) >= 2:
            quantiles = statistics.quantiles(confidences, n=20)
            # n=20 => 19 cut points: [0]=p5, [9]=p50, [18]=p95
            p5 = round(quantiles[0], 4)
            p50 = round(quantiles[9], 4)
            p95 = round(quantiles[18], 4)
        else:
            val = confidences[0] if confidences else 0.0
            p5 = p50 = p95 = round(val, 4)

        return CoverageMetrics(
            total_candidates=total,
            strong_key_pct=strong_key_pct,
            probabilistic_linkage_pct=probabilistic_linkage_pct,
            per_source_pct=per_source_pct,
            thin_record_pct=thin_record_pct,
            linkage_confidence_p5=p5,
            linkage_confidence_p50=p50,
            linkage_confidence_p95=p95,
        )

    def generate_html_report(self, metrics: CoverageMetrics) -> str:
        """Return an HTML string summarising the coverage metrics."""
        source_rows = "".join(
            f"<tr><td>{src}</td><td>{pct}%</td></tr>"
            for src, pct in metrics.per_source_pct.items()
        )
        # Simple bar chart via inline CSS
        source_bars = "".join(
            f'<div style="margin:4px 0;">'
            f'<span style="display:inline-block;width:80px;">{src}</span>'
            f'<span style="display:inline-block;width:{pct * 2}px;'
            f'height:18px;background:#4682b4;"></span>'
            f" {pct}%</div>"
            for src, pct in metrics.per_source_pct.items()
        )
        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Coverage Dashboard</title>
<style>
body {{ font-family: sans-serif; margin: 2em; }}
table {{ border-collapse: collapse; margin: 1em 0; }}
th, td {{ border: 1px solid #ccc; padding: 6px 12px; text-align: left; }}
th {{ background: #f0f0f0; }}
h1 {{ color: #333; }}
</style>
</head>
<body>
<h1>Coverage Diagnostics</h1>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Total Candidates</td><td>{metrics.total_candidates}</td></tr>
<tr><td>Strong-Key %</td><td>{metrics.strong_key_pct}%</td></tr>
<tr><td>Probabilistic Linkage %</td><td>{metrics.probabilistic_linkage_pct}%</td></tr>
<tr><td>Thin-Record %</td><td>{metrics.thin_record_pct}%</td></tr>
<tr><td>Linkage P5</td><td>{metrics.linkage_confidence_p5}</td></tr>
<tr><td>Linkage P50</td><td>{metrics.linkage_confidence_p50}</td></tr>
<tr><td>Linkage P95</td><td>{metrics.linkage_confidence_p95}</td></tr>
</table>
<h2>Per-Source Coverage</h2>
<table>
<tr><th>Source</th><th>Coverage</th></tr>
{source_rows}
</table>
<h2>Per-Source Bar Chart</h2>
{source_bars}
</body>
</html>"""

    def save_report(
        self,
        metrics: CoverageMetrics,
        path: str = "src/aegis/observability/coverage_dashboard.html",
    ) -> None:
        """Write the HTML report to disk."""
        html = self.generate_html_report(metrics)
        with open(path, "w") as f:
            f.write(html)

    def compare(
        self,
        current: CoverageMetrics,
        previous: CoverageMetrics,
    ) -> dict[str, float]:
        """Return deltas between two metric snapshots."""
        deltas: dict[str, float] = {
            "strong_key_pct": round(
                current.strong_key_pct - previous.strong_key_pct, 2
            ),
            "probabilistic_linkage_pct": round(
                current.probabilistic_linkage_pct
                - previous.probabilistic_linkage_pct,
                2,
            ),
            "thin_record_pct": round(
                current.thin_record_pct - previous.thin_record_pct, 2
            ),
            "linkage_confidence_p50": round(
                current.linkage_confidence_p50
                - previous.linkage_confidence_p50,
                4,
            ),
        }
        all_sources = set(current.per_source_pct) | set(
            previous.per_source_pct
        )
        for src in sorted(all_sources):
            cur = current.per_source_pct.get(src, 0.0)
            prev = previous.per_source_pct.get(src, 0.0)
            deltas[f"per_source_{src}"] = round(cur - prev, 2)
        return deltas
