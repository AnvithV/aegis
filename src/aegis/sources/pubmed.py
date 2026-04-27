"""PubMed E-utilities client returning typed PubMedRecord objects."""

from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator
from datetime import date
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryConfig, RetryPolicy
from aegis.storage.schema import MeshDescriptor

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class AuthorAffiliation(BaseModel):
    """Author record with affiliation strings and optional ORCID."""

    model_config = ConfigDict(frozen=True)

    full_name: str
    last_name: str
    initials: str
    orcid: str | None
    affiliations: list[str]
    is_last_author: bool


class PubMedRecord(BaseModel):
    """Structured representation of a PubMed article."""

    model_config = ConfigDict(frozen=True)

    pmid: str
    title: str
    abstract: str | None
    mesh_descriptors: list[MeshDescriptor]
    authors: list[AuthorAffiliation]
    journal_nlm_id: str | None
    medline_indexed: bool
    publication_date: date | None
    article_type: str | None
    raw_xml: str


class PubMedClient:
    """Typed client wrapping NCBI E-utilities (esearch + efetch)."""

    def __init__(
        self,
        api_key: str | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._api_key = api_key
        self._rate_limit = 10.0 if api_key else 3.0
        self._min_interval = 1.0 / self._rate_limit
        self._retry = retry_policy or RetryPolicy(RetryConfig())
        self._last_request_time: float = 0.0

    async def _throttle(self) -> None:
        """Enforce per-second rate limits."""
        import time

        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def _get(
        self, client: httpx.AsyncClient, url: str, params: dict[str, str]
    ) -> bytes:
        """Make a rate-limited GET request with retry."""
        if self._api_key:
            params["api_key"] = self._api_key

        async def _do_request() -> bytes:
            await self._throttle()
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.content

        return await self._retry.execute(_do_request)

    async def search_and_fetch(
        self,
        query: str,
        since: date | None = None,
        batch_size: int = 200,
    ) -> AsyncIterator[PubMedRecord]:
        """Search PubMed and yield full records in batches."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Build search query with optional date filter
            search_query = query
            if since is not None:
                search_query += f" AND {since.isoformat()}:3000[EDAT]"

            # First pass: get all PMIDs via esearch
            pmids: list[str] = []
            retstart = 0
            while True:
                params = {
                    "db": "pubmed",
                    "term": search_query,
                    "retmax": str(batch_size),
                    "retstart": str(retstart),
                    "retmode": "xml",
                    "usehistory": "n",
                }
                xml_bytes = await self._get(client, _ESEARCH_URL, params)
                root = ET.fromstring(xml_bytes)  # noqa: S314

                id_list = root.find("IdList")
                if id_list is None:
                    break
                batch_ids = [el.text for el in id_list.findall("Id") if el.text]
                if not batch_ids:
                    break
                pmids.extend(batch_ids)

                count_el = root.find("Count")
                total = (
                    int(count_el.text)
                    if count_el is not None and count_el.text
                    else 0
                )
                retstart += batch_size
                if retstart >= total:
                    break

            logger.info("esearch returned %d PMIDs for query: %s", len(pmids), query)

            # Second pass: fetch full records in batches
            for i in range(0, len(pmids), batch_size):
                batch = pmids[i : i + batch_size]
                params = {
                    "db": "pubmed",
                    "id": ",".join(batch),
                    "retmode": "xml",
                    "rettype": "full",
                }
                xml_bytes = await self._get(client, _EFETCH_URL, params)
                records = self._parse_efetch_xml(xml_bytes)
                for record in records:
                    yield record

    def _parse_efetch_xml(self, xml_bytes: bytes) -> list[PubMedRecord]:
        """Parse PubMed efetch XML into typed records."""
        root = ET.fromstring(xml_bytes)  # noqa: S314
        records: list[PubMedRecord] = []

        for article_el in root.findall(".//PubmedArticle"):
            records.append(self._parse_article(article_el, xml_bytes))

        return records

    def _parse_article(
        self, article_el: ET.Element, raw_xml_bytes: bytes
    ) -> PubMedRecord:
        """Parse a single PubmedArticle element."""
        medline = article_el.find("MedlineCitation")
        assert medline is not None  # noqa: S101

        # PMID
        pmid_el = medline.find("PMID")
        pmid = pmid_el.text if pmid_el is not None and pmid_el.text else ""

        # Medline status
        status = medline.get("Status", "")
        medline_indexed = status.lower() == "medline"

        article = medline.find("Article")
        assert article is not None  # noqa: S101

        # Title
        title_el = article.find("ArticleTitle")
        title = self._get_text(title_el) if title_el is not None else ""

        # Abstract
        abstract_el = article.find("Abstract/AbstractText")
        abstract = self._get_text(abstract_el) if abstract_el is not None else None

        # Journal NLM ID
        journal_info = medline.find("MedlineJournalInfo/NlmUniqueID")
        journal_nlm_id = journal_info.text if journal_info is not None else None

        # Publication date
        pub_date = self._parse_pub_date(article)

        # Article type
        pub_type_el = article.find(".//PublicationType")
        article_type = pub_type_el.text if pub_type_el is not None else None

        # Authors
        authors = self._parse_authors(article)

        # MeSH descriptors
        mesh_descriptors = self._parse_mesh(medline)

        # Raw XML for the individual article
        raw_xml = ET.tostring(article_el, encoding="unicode")

        return PubMedRecord(
            pmid=pmid,
            title=title,
            abstract=abstract,
            mesh_descriptors=mesh_descriptors,
            authors=authors,
            journal_nlm_id=journal_nlm_id,
            medline_indexed=medline_indexed,
            publication_date=pub_date,
            article_type=article_type,
            raw_xml=raw_xml,
        )

    @staticmethod
    def _get_text(el: ET.Element) -> str:
        """Get all text content from an element, including tails of children."""
        return "".join(el.itertext())

    @staticmethod
    def _parse_pub_date(article: ET.Element) -> date | None:
        """Extract publication date from article."""
        for date_path in [
            "Journal/JournalIssue/PubDate",
            "ArticleDate",
        ]:
            date_el = article.find(date_path)
            if date_el is None:
                continue
            year_el = date_el.find("Year")
            month_el = date_el.find("Month")
            day_el = date_el.find("Day")
            if year_el is not None and year_el.text:
                year = int(year_el.text)
                month = (
                    int(month_el.text)
                    if month_el is not None
                    and month_el.text
                    and month_el.text.isdigit()
                    else 1
                )
                day = (
                    int(day_el.text)
                    if day_el is not None and day_el.text
                    else 1
                )
                try:
                    return date(year, month, day)
                except ValueError:
                    return date(year, 1, 1)
        return None

    @staticmethod
    def _parse_authors(article: ET.Element) -> list[AuthorAffiliation]:
        """Parse author list from article element."""
        authors: list[AuthorAffiliation] = []
        author_list = article.find("AuthorList")
        if author_list is None:
            return authors

        author_els = author_list.findall("Author")
        for idx, author_el in enumerate(author_els):
            last_name_el = author_el.find("LastName")
            fore_name_el = author_el.find("ForeName")
            initials_el = author_el.find("Initials")

            last_name = (
                last_name_el.text
                if last_name_el is not None and last_name_el.text
                else ""
            )
            fore_name = (
                fore_name_el.text
                if fore_name_el is not None and fore_name_el.text
                else ""
            )
            initials = (
                initials_el.text
                if initials_el is not None and initials_el.text
                else ""
            )

            full_name = f"{fore_name} {last_name}".strip() if fore_name else last_name

            # ORCID extraction from Identifier elements
            orcid: str | None = None
            for ident in author_el.findall("Identifier"):
                source = ident.get("Source", "")
                if source.upper() == "ORCID" and ident.text:
                    orcid_text = ident.text.strip()
                    # Normalize: strip URL prefix if present
                    if "/" in orcid_text:
                        orcid_text = orcid_text.rsplit("/", 1)[-1]
                    orcid = orcid_text

            # Affiliations
            affiliations = [
                aff.text
                for aff in author_el.findall("AffiliationInfo/Affiliation")
                if aff.text
            ]

            is_last = idx == len(author_els) - 1

            authors.append(
                AuthorAffiliation(
                    full_name=full_name,
                    last_name=last_name,
                    initials=initials,
                    orcid=orcid,
                    affiliations=affiliations,
                    is_last_author=is_last,
                )
            )

        return authors

    @staticmethod
    def _parse_mesh(medline: ET.Element) -> list[MeshDescriptor]:
        """Parse MeSH heading list from MedlineCitation."""
        descriptors: list[MeshDescriptor] = []
        mesh_list = medline.find("MeshHeadingList")
        if mesh_list is None:
            return descriptors

        for heading in mesh_list.findall("MeshHeading"):
            desc_el = heading.find("DescriptorName")
            if desc_el is None or not desc_el.text:
                continue

            desc_name = desc_el.text
            desc_major = desc_el.get("MajorTopicYN", "N") == "Y"

            # A heading without qualifiers
            qualifier_els = heading.findall("QualifierName")
            if not qualifier_els:
                descriptors.append(
                    MeshDescriptor(
                        descriptor=desc_name,
                        qualifier=None,
                        major_topic=desc_major,
                    )
                )
            else:
                for qual_el in qualifier_els:
                    qual_name = qual_el.text if qual_el.text else None
                    # Major topic is true if either descriptor or qualifier is major
                    qual_major = qual_el.get("MajorTopicYN", "N") == "Y"
                    descriptors.append(
                        MeshDescriptor(
                            descriptor=desc_name,
                            qualifier=qual_name,
                            major_topic=desc_major or qual_major,
                        )
                    )

        return descriptors
