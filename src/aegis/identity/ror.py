"""ROR-normalized affiliation resolver with fuzzy matching and alias support."""

from __future__ import annotations

import functools
import logging
import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict
from thefuzz import fuzz  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Curated subset of biomed-relevant ROR records for Phase 0.
# Each entry: canonical_name -> {ror_id, parent_ror_id, parent_name, country}
_CURATED_ROR: dict[str, dict[str, str | None]] = {
    "Massachusetts General Hospital": {
        "ror_id": "https://ror.org/002pd6e78",
        "parent_ror_id": "https://ror.org/04b6nzv94",
        "parent_name": "Mass General Brigham",
        "country": "US",
    },
    "Mass General Brigham": {
        "ror_id": "https://ror.org/04b6nzv94",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Harvard Medical School": {
        "ror_id": "https://ror.org/03vek6s52",
        "parent_ror_id": "https://ror.org/03vek6s52",
        "parent_name": "Harvard University",
        "country": "US",
    },
    "Harvard University": {
        "ror_id": "https://ror.org/03vek6s52",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Brigham and Women's Hospital": {
        "ror_id": "https://ror.org/04b6nzv94",
        "parent_ror_id": "https://ror.org/04b6nzv94",
        "parent_name": "Mass General Brigham",
        "country": "US",
    },
    "Dana-Farber Cancer Institute": {
        "ror_id": "https://ror.org/02jzgtq86",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Memorial Sloan Kettering Cancer Center": {
        "ror_id": "https://ror.org/02yrq0923",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "University of Texas MD Anderson Cancer Center": {
        "ror_id": "https://ror.org/04twxam07",
        "parent_ror_id": "https://ror.org/02f6dcw23",
        "parent_name": "University of Texas System",
        "country": "US",
    },
    "National Institutes of Health": {
        "ror_id": "https://ror.org/01cwqze88",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "National Cancer Institute": {
        "ror_id": "https://ror.org/040gcmg81",
        "parent_ror_id": "https://ror.org/01cwqze88",
        "parent_name": "National Institutes of Health",
        "country": "US",
    },
    "University of California, San Francisco": {
        "ror_id": "https://ror.org/043mz5j54",
        "parent_ror_id": "https://ror.org/00pjhtq55",
        "parent_name": "University of California System",
        "country": "US",
    },
    "University of California, Los Angeles": {
        "ror_id": "https://ror.org/046rm7j60",
        "parent_ror_id": "https://ror.org/00pjhtq55",
        "parent_name": "University of California System",
        "country": "US",
    },
    "Stanford University": {
        "ror_id": "https://ror.org/00f54p054",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Mayo Clinic": {
        "ror_id": "https://ror.org/02qp3tb03",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Johns Hopkins University": {
        "ror_id": "https://ror.org/00za53h95",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "University of Pennsylvania": {
        "ror_id": "https://ror.org/00b30xv10",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Yale University": {
        "ror_id": "https://ror.org/03v76x132",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Columbia University": {
        "ror_id": "https://ror.org/00hj8s172",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Duke University": {
        "ror_id": "https://ror.org/00py81415",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Emory University": {
        "ror_id": "https://ror.org/03czfpz43",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Washington University in St. Louis": {
        "ror_id": "https://ror.org/01yc7t268",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "University of Chicago": {
        "ror_id": "https://ror.org/024mw5h28",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "University of Michigan": {
        "ror_id": "https://ror.org/00jmfr291",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Vanderbilt University": {
        "ror_id": "https://ror.org/02vm5rt34",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Vanderbilt University Medical Center": {
        "ror_id": "https://ror.org/05dq2gs74",
        "parent_ror_id": "https://ror.org/02vm5rt34",
        "parent_name": "Vanderbilt University",
        "country": "US",
    },
    "Icahn School of Medicine at Mount Sinai": {
        "ror_id": "https://ror.org/04a9tmd77",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Oregon Health & Science University": {
        "ror_id": "https://ror.org/009avj582",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Karolinska Institutet": {
        "ror_id": "https://ror.org/056d84691",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "SE",
    },
    "University College London": {
        "ror_id": "https://ror.org/02jx3x895",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "University of Oxford": {
        "ror_id": "https://ror.org/052gg0110",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "University of Cambridge": {
        "ror_id": "https://ror.org/013meh722",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "Imperial College London": {
        "ror_id": "https://ror.org/041kmwe10",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "Institut National de la Santé et de la Recherche Médicale": {
        "ror_id": "https://ror.org/02vjkv261",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "FR",
    },
    "Charité – Universitätsmedizin Berlin": {
        "ror_id": "https://ror.org/001w7jn25",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "DE",
    },
    "University Health Network": {
        "ror_id": "https://ror.org/042xt5161",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CA",
    },
    "Princess Margaret Cancer Centre": {
        "ror_id": "https://ror.org/033yphy03",
        "parent_ror_id": "https://ror.org/042xt5161",
        "parent_name": "University Health Network",
        "country": "CA",
    },
    "Peter MacCallum Cancer Centre": {
        "ror_id": "https://ror.org/02a8bt934",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "AU",
    },
    "National University of Singapore": {
        "ror_id": "https://ror.org/01tgyzw49",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "SG",
    },
    "University of Tokyo": {
        "ror_id": "https://ror.org/057zh3y96",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "JP",
    },
    "Peking University": {
        "ror_id": "https://ror.org/02v51f717",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CN",
    },
    "Fudan University": {
        "ror_id": "https://ror.org/013q1eq08",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CN",
    },
    "Centre National de la Recherche Scientifique": {
        "ror_id": "https://ror.org/02feahw73",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "FR",
    },
    "RIKEN": {
        "ror_id": "https://ror.org/01sjwvz98",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "JP",
    },
    "Max Planck Society": {
        "ror_id": "https://ror.org/01hhn8329",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "DE",
    },
    "Broad Institute": {
        "ror_id": "https://ror.org/05a0ya142",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Massachusetts Institute of Technology": {
        "ror_id": "https://ror.org/042nb2s44",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "University of Washington": {
        "ror_id": "https://ror.org/00cvxb145",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "University of Pittsburgh": {
        "ror_id": "https://ror.org/01an3r305",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "University of North Carolina at Chapel Hill": {
        "ror_id": "https://ror.org/0130frc33",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "Baylor College of Medicine": {
        "ror_id": "https://ror.org/02pttbw34",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "US",
    },
    "University of Toronto": {
        "ror_id": "https://ror.org/03dbr7087",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CA",
    },
    # ── Phase 3d: International expansion ──────────────────────────
    # Japan (JP)
    "Kyoto University": {
        "ror_id": "https://ror.org/02kpeqv85",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "JP",
    },
    "Osaka University": {
        "ror_id": "https://ror.org/035t8zc32",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "JP",
    },
    "Tohoku University": {
        "ror_id": "https://ror.org/01dq60k83",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "JP",
    },
    "Nagoya University": {
        "ror_id": "https://ror.org/04chrp450",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "JP",
    },
    "National Institute of Advanced Industrial Science and Technology": {
        "ror_id": "https://ror.org/01703db54",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "JP",
    },
    "Keio University": {
        "ror_id": "https://ror.org/02kn6nx58",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "JP",
    },
    "Hokkaido University": {
        "ror_id": "https://ror.org/02e16g702",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "JP",
    },
    "Kyushu University": {
        "ror_id": "https://ror.org/00p4k0j84",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "JP",
    },
    # China (CN)
    "Tsinghua University": {
        "ror_id": "https://ror.org/03cve4549",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CN",
    },
    "Zhejiang University": {
        "ror_id": "https://ror.org/00a2xv884",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CN",
    },
    "Shanghai Jiao Tong University": {
        "ror_id": "https://ror.org/0220qvk04",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CN",
    },
    "Sun Yat-sen University": {
        "ror_id": "https://ror.org/0064kty71",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CN",
    },
    "Chinese Academy of Sciences": {
        "ror_id": "https://ror.org/034t30j35",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CN",
    },
    "Nanjing University": {
        "ror_id": "https://ror.org/01rxvg760",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CN",
    },
    "Wuhan University": {
        "ror_id": "https://ror.org/033vjfk17",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CN",
    },
    "Huazhong University of Science and Technology": {
        "ror_id": "https://ror.org/00p991c53",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CN",
    },
    # UK (GB)
    "King's College London": {
        "ror_id": "https://ror.org/0220mzb33",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "University of Edinburgh": {
        "ror_id": "https://ror.org/01nrxwf90",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "University of Manchester": {
        "ror_id": "https://ror.org/027m9bs27",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "University of Glasgow": {
        "ror_id": "https://ror.org/00vtgdb53",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "Francis Crick Institute": {
        "ror_id": "https://ror.org/048s57834",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "University of Bristol": {
        "ror_id": "https://ror.org/0524sp257",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "University of Birmingham": {
        "ror_id": "https://ror.org/03angcq70",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    "University of Leeds": {
        "ror_id": "https://ror.org/024mrxd33",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "GB",
    },
    # Canada (CA)
    "McGill University": {
        "ror_id": "https://ror.org/01pxwe438",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CA",
    },
    "University of British Columbia": {
        "ror_id": "https://ror.org/03rmrcq20",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CA",
    },
    "University of Alberta": {
        "ror_id": "https://ror.org/0160cpw27",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CA",
    },
    "McMaster University": {
        "ror_id": "https://ror.org/02fa3aq29",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CA",
    },
    "University of Montreal": {
        "ror_id": "https://ror.org/0161xgx34",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CA",
    },
    "Ottawa Hospital Research Institute": {
        "ror_id": "https://ror.org/03c4atk17",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CA",
    },
    "University of Calgary": {
        "ror_id": "https://ror.org/03yjb2x39",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CA",
    },
    "Dalhousie University": {
        "ror_id": "https://ror.org/01e6qks80",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CA",
    },
    # EU (various countries)
    "ETH Zurich": {
        "ror_id": "https://ror.org/05a28rw58",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CH",
    },
    "Leiden University": {
        "ror_id": "https://ror.org/027bh9e22",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "NL",
    },
    "University of Copenhagen": {
        "ror_id": "https://ror.org/035b05819",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "DK",
    },
    "Helmholtz Association": {
        "ror_id": "https://ror.org/0281dp749",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "DE",
    },
    "Pasteur Institute": {
        "ror_id": "https://ror.org/0495fxg12",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "FR",
    },
    "University of Zurich": {
        "ror_id": "https://ror.org/02crff812",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "CH",
    },
    "KU Leuven": {
        "ror_id": "https://ror.org/05f950310",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "BE",
    },
    "University of Amsterdam": {
        "ror_id": "https://ror.org/04dkp9463",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "NL",
    },
    "Ludwig Maximilian University of Munich": {
        "ror_id": "https://ror.org/05591te55",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "DE",
    },
    "University of Helsinki": {
        "ror_id": "https://ror.org/040af2s02",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "FI",
    },
    "Sapienza University of Rome": {
        "ror_id": "https://ror.org/02be6w209",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "IT",
    },
    "University of Barcelona": {
        "ror_id": "https://ror.org/021018s57",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "ES",
    },
    "Erasmus University Rotterdam": {
        "ror_id": "https://ror.org/018906e22",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "NL",
    },
    "Uppsala University": {
        "ror_id": "https://ror.org/048a87296",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "SE",
    },
    "Technical University of Munich": {
        "ror_id": "https://ror.org/02kkvpp62",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "DE",
    },
    # Australia (AU)
    "University of Melbourne": {
        "ror_id": "https://ror.org/01ej9dk98",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "AU",
    },
    "University of Sydney": {
        "ror_id": "https://ror.org/0384j8v12",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "AU",
    },
    "Monash University": {
        "ror_id": "https://ror.org/02bfwt286",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "AU",
    },
    "University of Queensland": {
        "ror_id": "https://ror.org/00rqy9422",
        "parent_ror_id": None,
        "parent_name": None,
        "country": "AU",
    },
}

# Common abbreviation expansions for biomedical affiliations.
_ABBREVIATIONS: dict[str, str] = {
    "univ": "university",
    "hosp": "hospital",
    "med": "medical",
    "dept": "department",
    "ctr": "center",
    "inst": "institute",
    "sch": "school",
    "sci": "science",
    "res": "research",
    "natl": "national",
    "intl": "international",
    "coll": "college",
    "hlth": "health",
}


class RorMatch(BaseModel):
    """Result of ROR affiliation resolution."""

    model_config = ConfigDict(frozen=True)

    ror_id: str
    canonical_name: str
    parent_ror_id: str | None
    parent_name: str | None
    country: str | None
    confidence: float
    matched_via: str


class RorResolver:
    """Resolve raw affiliation strings to ROR records."""

    def __init__(
        self,
        aliases_path: str | None = None,
        cache_size: int = 10000,
    ) -> None:
        if aliases_path is None:
            aliases_path = str(
                Path(__file__).parent / "ror_aliases.yaml"
            )
        self._aliases = self._load_aliases(aliases_path)
        self._ror_data = self._load_ror_data()
        # Build lowercase lookup index for ROR names
        self._name_index: dict[str, str] = {
            name.lower(): name for name in self._ror_data
        }
        # Wrap resolve with LRU cache
        self._cached_resolve = functools.lru_cache(maxsize=cache_size)(
            self._resolve_impl
        )

    def resolve(self, affiliation_string: str) -> RorMatch | None:
        """Resolve an affiliation string to a ROR record with confidence."""
        if not affiliation_string or not affiliation_string.strip():
            return None
        return self._cached_resolve(affiliation_string)

    def resolve_batch(
        self, affiliations: list[str]
    ) -> list[RorMatch | None]:
        """Resolve a batch of affiliation strings."""
        return [self.resolve(a) for a in affiliations]

    def _resolve_impl(self, affiliation_string: str) -> RorMatch | None:
        """Core resolution logic (cached externally)."""
        normalized = self._normalize(affiliation_string)

        # Step 1: Check alias list for exact match
        alias_match = self._check_alias(normalized)
        if alias_match is not None:
            return alias_match

        # Step 2: Exact match against ROR canonical names
        if normalized in self._name_index:
            canonical = self._name_index[normalized]
            entry = self._ror_data[canonical]
            return RorMatch(
                ror_id=entry["ror_id"],  # type: ignore[arg-type]
                canonical_name=canonical,
                parent_ror_id=entry.get("parent_ror_id"),
                parent_name=entry.get("parent_name"),
                country=entry.get("country"),
                confidence=1.0,
                matched_via="exact",
            )

        # Step 3: Fuzzy match against all ROR names
        expanded = self._expand_abbreviations(normalized)
        best_score = 0
        best_name = ""
        for canonical_name in self._ror_data:
            score = fuzz.ratio(expanded, canonical_name.lower())
            if score > best_score:
                best_score = score
                best_name = canonical_name

        if not best_name:
            return None

        confidence = best_score / 100.0
        entry = self._ror_data[best_name]
        matched_via = "fuzzy" if confidence >= 0.7 else "fuzzy-low"

        return RorMatch(
            ror_id=entry["ror_id"],  # type: ignore[arg-type]
            canonical_name=best_name,
            parent_ror_id=entry.get("parent_ror_id"),
            parent_name=entry.get("parent_name"),
            country=entry.get("country"),
            confidence=confidence,
            matched_via=matched_via,
        )

    def _normalize(self, text: str) -> str:
        """Lowercase, strip whitespace, collapse internal spaces."""
        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def _expand_abbreviations(self, text: str) -> str:
        """Expand common biomedical abbreviations in text."""
        words = text.split()
        expanded = []
        for word in words:
            clean = word.strip(".,;:()")
            if clean in _ABBREVIATIONS:
                expanded.append(
                    word.replace(clean, _ABBREVIATIONS[clean])
                )
            else:
                expanded.append(word)
        return " ".join(expanded)

    def _check_alias(self, normalized: str) -> RorMatch | None:
        """Check if the normalized string matches an alias."""
        for alias_key, canonical_name in self._aliases.items():
            if normalized == alias_key.lower():
                entry = self._ror_data.get(canonical_name)
                if entry is None:
                    continue
                return RorMatch(
                    ror_id=entry["ror_id"],  # type: ignore[arg-type]
                    canonical_name=canonical_name,
                    parent_ror_id=entry.get("parent_ror_id"),
                    parent_name=entry.get("parent_name"),
                    country=entry.get("country"),
                    confidence=1.0,
                    matched_via="alias",
                )
        return None

    @staticmethod
    def _load_aliases(path: str) -> dict[str, str]:
        """Load alias mappings from YAML file."""
        p = Path(path)
        if not p.exists():
            logger.warning("Alias file not found: %s", path)
            return {}
        with p.open() as f:
            data: dict[str, Any] = yaml.safe_load(f)
        aliases: dict[str, str] = data.get("aliases", {})
        return aliases

    @staticmethod
    def _load_ror_data() -> dict[str, dict[str, str | None]]:
        """Load curated ROR data subset for Phase 0.

        Returns a mapping of canonical_name -> metadata dict.
        """
        return dict(_CURATED_ROR)
