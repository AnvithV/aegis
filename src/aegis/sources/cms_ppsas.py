"""CMS Medicare Provider Utilization & Payment (PPSAS) data client."""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class ProviderUtilization(BaseModel):
    """Medicare provider utilization record."""

    model_config = ConfigDict(frozen=True)

    npi: str
    provider_name: str
    credential: str | None
    hcpcs_code: str                # CPT/HCPCS code
    hcpcs_description: str
    total_services: int
    total_beneficiaries: int
    average_submitted_charge: float | None
    average_medicare_payment: float | None


class CmsPpsasClient:
    """Ingest CMS Medicare Provider Utilization and Payment data.

    Public data: Medicare Provider Utilization and Payment Data (PPSAS)
    provides per-NPI, per-procedure volume proxies.
    """

    def iter_utilization(
        self, file_path: Path, npi_filter: set[str] | None = None
    ) -> Iterator[ProviderUtilization]:
        """Stream provider utilization records from CMS CSV.

        Args:
            file_path: Path to CMS PPSAS CSV file
            npi_filter: If provided, only yield records for these NPIs
        """
        with open(file_path, newline="", encoding="utf-8") as f:  # noqa: PTH123
            reader = csv.DictReader(f)
            for row in reader:
                npi = row.get("Rndrng_NPI", "").strip()
                if not npi:
                    continue
                if npi_filter and npi not in npi_filter:
                    continue

                try:
                    yield ProviderUtilization(
                        npi=npi,
                        provider_name=row.get("Rndrng_Prvdr_Last_Org_Name", ""),
                        credential=row.get("Rndrng_Prvdr_Crdntls"),
                        hcpcs_code=row.get("HCPCS_Cd", ""),
                        hcpcs_description=row.get("HCPCS_Desc", ""),
                        total_services=int(float(row.get("Tot_Srvcs", "0"))),
                        total_beneficiaries=int(float(row.get("Tot_Benes", "0"))),
                        average_submitted_charge=self._parse_float(row.get("Avg_Sbmtd_Chrg")),
                        average_medicare_payment=self._parse_float(row.get("Avg_Mdcr_Pymt_Amt")),
                    )
                except (ValueError, KeyError) as exc:
                    logger.debug("CMS PPSAS parse error: %s", exc)

    @staticmethod
    def _parse_float(val: str | None) -> float | None:
        if val is None or val.strip() == "":
            return None
        try:
            return float(val.replace(",", ""))
        except ValueError:
            return None

    def aggregate_by_npi(
        self, file_path: Path, npi_filter: set[str] | None = None
    ) -> dict[str, dict[str, int]]:
        """Aggregate total services per HCPCS code per NPI.

        Returns {npi: {hcpcs_code: total_services}}.
        """
        result: dict[str, dict[str, int]] = {}
        for record in self.iter_utilization(file_path, npi_filter):
            if record.npi not in result:
                result[record.npi] = {}
            existing = result[record.npi].get(record.hcpcs_code, 0)
            result[record.npi][record.hcpcs_code] = existing + record.total_services
        return result
