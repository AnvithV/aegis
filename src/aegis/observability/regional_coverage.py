"""Per-region coverage diagnostics for geographic bias detection."""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from aegis.sources.non_us_grants import Region, candidate_region

if TYPE_CHECKING:
    from aegis.storage.candidate_store import CandidateStore
    from aegis.storage.schema import Candidate

REGIONAL_CAVEAT_THRESHOLD = 75.0


class RegionalCoverageMetrics(BaseModel):
    """Frozen snapshot of per-region coverage statistics."""

    model_config = ConfigDict(frozen=True)

    total_candidates: int
    per_region_count: dict[str, int]
    per_region_pct: dict[str, float]
    non_us_ratio: float
    dominant_region: str
    dominant_region_pct: float
    is_geographically_biased: bool
    per_region_linkage_confidence: dict[str, float]
    per_region_source_coverage: dict[str, dict[str, float]]
    coverage_caveats: list[str]
    regional_caveat: str | None


def build_regional_caveat(dominant_region: str, pct: float) -> str:
    """Build a human-readable caveat for geographically biased results."""
    return (
        f"Results are >75% from {dominant_region} ({pct:.1f}%). "
        f"Coverage for other regions may be incomplete. "
        f"Interpret global ranking with this regional weighting in mind."
    )


class RegionalCoverageDashboard:
    """Compute per-region coverage metrics from a CandidateStore."""

    def __init__(self, store: CandidateStore) -> None:
        self._store = store

    def compute(
        self, cohort_candidates: list[str] | None = None
    ) -> RegionalCoverageMetrics:
        """Compute regional coverage for the cohort or a subset of UUIDs."""
        if cohort_candidates is not None:
            candidates: list[Candidate] = []
            for uuid in cohort_candidates:
                c = self._store.get_by_uuid(uuid)
                if c is not None:
                    candidates.append(c)
        else:
            candidates = self._store.list_by_cohort()

        total = len(candidates)
        if total == 0:
            return RegionalCoverageMetrics(
                total_candidates=0,
                per_region_count={r.value: 0 for r in Region},
                per_region_pct={r.value: 0.0 for r in Region},
                non_us_ratio=0.0,
                dominant_region=Region.REST_OF_WORLD.value,
                dominant_region_pct=0.0,
                is_geographically_biased=False,
                per_region_linkage_confidence={r.value: 0.0 for r in Region},
                per_region_source_coverage={},
                coverage_caveats=[],
                regional_caveat=None,
            )

        # Derive region for each candidate
        region_map: dict[str, list[Candidate]] = {r.value: [] for r in Region}
        for c in candidates:
            region = candidate_region(c.affiliations)
            region_map[region.value].append(c)

        # Per-region counts and percentages
        per_region_count = {r: len(cands) for r, cands in region_map.items()}
        per_region_pct = {
            r: round(100.0 * cnt / total, 2) for r, cnt in per_region_count.items()
        }

        # Non-US ratio
        us_count = per_region_count.get(Region.US.value, 0)
        non_us_ratio = round((total - us_count) / total, 4) if total > 0 else 0.0

        # Dominant region
        dominant_region = max(per_region_count, key=lambda r: per_region_count[r])
        dominant_region_pct = per_region_pct[dominant_region]
        is_biased = dominant_region_pct > REGIONAL_CAVEAT_THRESHOLD

        # Per-region median linkage confidence
        per_region_linkage: dict[str, float] = {}
        for r, cands in region_map.items():
            if cands:
                confs = [c.linkage_confidence for c in cands]
                per_region_linkage[r] = round(statistics.median(confs), 4)
            else:
                per_region_linkage[r] = 0.0

        # Per-region source coverage
        sources = ["pubmed", "reporter", "ctgov", "patent"]
        per_region_source: dict[str, dict[str, float]] = {}
        for r, cands in region_map.items():
            if not cands:
                continue
            src_counts: dict[str, int] = {s: 0 for s in sources}
            for c in cands:
                if c.artifact_refs.pmids:
                    src_counts["pubmed"] += 1
                if c.artifact_refs.grant_ids:
                    src_counts["reporter"] += 1
                if c.artifact_refs.nct_ids:
                    src_counts["ctgov"] += 1
                if c.artifact_refs.patent_ids:
                    src_counts["patent"] += 1
            per_region_source[r] = {
                s: round(100.0 * cnt / len(cands), 2)
                for s, cnt in src_counts.items()
            }

        # Coverage caveats
        caveats: list[str] = []
        if per_region_count.get(Region.CHINA.value, 0) > 0:
            caveats.append(
                "NSFC coverage is partial -- not all Chinese-funded projects are "
                "publicly accessible."
            )

        # Regional caveat
        regional_caveat: str | None = None
        if is_biased:
            regional_caveat = build_regional_caveat(
                dominant_region, dominant_region_pct
            )

        return RegionalCoverageMetrics(
            total_candidates=total,
            per_region_count=per_region_count,
            per_region_pct=per_region_pct,
            non_us_ratio=non_us_ratio,
            dominant_region=dominant_region,
            dominant_region_pct=dominant_region_pct,
            is_geographically_biased=is_biased,
            per_region_linkage_confidence=per_region_linkage,
            per_region_source_coverage=per_region_source,
            coverage_caveats=caveats,
            regional_caveat=regional_caveat,
        )

    def generate_html_report(self, metrics: RegionalCoverageMetrics) -> str:
        """HTML dashboard with per-region bar chart and bias warning."""
        region_rows = "".join(
            f"<tr><td>{r}</td><td>{metrics.per_region_count[r]}</td>"
            f"<td>{metrics.per_region_pct[r]}%</td></tr>"
            for r in metrics.per_region_count
        )
        region_bars = "".join(
            f'<div style="margin:4px 0;">'
            f'<span style="display:inline-block;width:120px;">{r}</span>'
            f'<span style="display:inline-block;width:{pct * 2}px;'
            f'height:18px;background:#4682b4;"></span>'
            f" {pct}%</div>"
            for r, pct in metrics.per_region_pct.items()
        )
        bias_warning = ""
        if metrics.is_geographically_biased and metrics.regional_caveat:
            bias_warning = (
                f'<div style="background:#fff3cd;padding:12px;border:1px solid '
                f'#ffc107;margin:1em 0;border-radius:4px;">'
                f"<strong>Geographic Bias Warning:</strong> "
                f"{metrics.regional_caveat}</div>"
            )
        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Regional Coverage Dashboard</title>
<style>
body {{ font-family: sans-serif; margin: 2em; }}
table {{ border-collapse: collapse; margin: 1em 0; }}
th, td {{ border: 1px solid #ccc; padding: 6px 12px; text-align: left; }}
th {{ background: #f0f0f0; }}
</style>
</head>
<body>
<h1>Regional Coverage Diagnostics</h1>
{bias_warning}
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Total Candidates</td><td>{metrics.total_candidates}</td></tr>
<tr><td>Non-US Ratio</td><td>{metrics.non_us_ratio:.1%}</td></tr>
<tr><td>Dominant Region</td>\
<td>{metrics.dominant_region} ({metrics.dominant_region_pct}%)</td></tr>
<tr><td>Geographically Biased</td><td>{metrics.is_geographically_biased}</td></tr>
</table>
<h2>Per-Region Breakdown</h2>
<table>
<tr><th>Region</th><th>Count</th><th>Percentage</th></tr>
{region_rows}
</table>
<h2>Per-Region Bar Chart</h2>
{region_bars}
</body>
</html>"""

    def compare(
        self,
        current: RegionalCoverageMetrics,
        previous: RegionalCoverageMetrics,
    ) -> dict[str, float]:
        """Return deltas between two snapshots."""
        deltas: dict[str, float] = {}
        deltas["total_candidates_delta"] = float(
            current.total_candidates - previous.total_candidates
        )
        deltas["non_us_ratio_delta"] = round(
            current.non_us_ratio - previous.non_us_ratio, 4
        )
        for region in current.per_region_pct:
            cur_pct = current.per_region_pct.get(region, 0.0)
            prev_pct = previous.per_region_pct.get(region, 0.0)
            deltas[f"{region}_pct_delta"] = round(cur_pct - prev_pct, 2)
        return deltas
