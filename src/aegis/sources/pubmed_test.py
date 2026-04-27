"""Tests for the PubMed E-utilities client (fixture-based, no live API calls)."""

from __future__ import annotations

import pytest

from aegis.sources.pubmed import PubMedClient, PubMedRecord

# ── Fixture XML ────────────────────────────────────────────────────────────────
EFETCH_XML = b"""\
<?xml version="1.0" ?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2024//EN"
  "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_240101.dtd">
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE" Owner="NLM">
      <PMID Version="1">12345678</PMID>
      <Article PubModel="Print">
        <Journal>
          <JournalIssue CitedMedium="Print">
            <PubDate>
              <Year>2024</Year>
              <Month>03</Month>
              <Day>15</Day>
            </PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Targeted Therapy in Non-Small Cell Lung Cancer</ArticleTitle>
        <Abstract>
          <AbstractText>This study evaluates novel targeted therapies.</AbstractText>
        </Abstract>
        <AuthorList CompleteYN="Y">
          <Author ValidYN="Y">
            <LastName>Smith</LastName>
            <ForeName>John A</ForeName>
            <Initials>JA</Initials>
            <Identifier Source="ORCID">https://orcid.org/0000-0001-2345-6789</Identifier>
            <AffiliationInfo>
              <Affiliation>Dept of Oncology, Harvard, Boston</Affiliation>
            </AffiliationInfo>
          </Author>
          <Author ValidYN="Y">
            <LastName>Doe</LastName>
            <ForeName>Jane B</ForeName>
            <Initials>JB</Initials>
            <AffiliationInfo>
              <Affiliation>Dept of Medicine, Stanford, CA</Affiliation>
            </AffiliationInfo>
          </Author>
        </AuthorList>
        <PublicationTypeList>
          <PublicationType UI="D016428">Journal Article</PublicationType>
        </PublicationTypeList>
      </Article>
      <MedlineJournalInfo>
        <NlmUniqueID>7505876</NlmUniqueID>
      </MedlineJournalInfo>
      <MeshHeadingList>
        <MeshHeading>
          <DescriptorName UI="D002289" MajorTopicYN="Y">Lung Neoplasms</DescriptorName>
          <QualifierName UI="Q000188" MajorTopicYN="N">drug therapy</QualifierName>
        </MeshHeading>
        <MeshHeading>
          <DescriptorName UI="D006801" MajorTopicYN="N">Humans</DescriptorName>
        </MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


@pytest.fixture
def client() -> PubMedClient:
    return PubMedClient()


def test_parse_efetch_xml(client: PubMedClient) -> None:
    """Parse fixture XML and verify core fields."""
    records = client._parse_efetch_xml(EFETCH_XML)

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, PubMedRecord)
    assert rec.pmid == "12345678"
    assert "Targeted Therapy" in rec.title
    assert rec.abstract is not None
    assert "novel targeted therapies" in rec.abstract

    # Authors
    assert len(rec.authors) == 2
    assert rec.authors[0].full_name == "John A Smith"
    assert rec.authors[1].full_name == "Jane B Doe"

    # MeSH
    assert len(rec.mesh_descriptors) == 2
    lung = rec.mesh_descriptors[0]
    assert lung.descriptor == "Lung Neoplasms"
    assert lung.qualifier == "drug therapy"

    humans = rec.mesh_descriptors[1]
    assert humans.descriptor == "Humans"
    assert humans.qualifier is None

    # Journal
    assert rec.journal_nlm_id == "7505876"

    # Date
    assert rec.publication_date is not None
    assert rec.publication_date.year == 2024
    assert rec.publication_date.month == 3


def test_mesh_major_topic_preserved(client: PubMedClient) -> None:
    """MeSH major-topic flag and qualifier are correctly parsed."""
    records = client._parse_efetch_xml(EFETCH_XML)
    rec = records[0]

    lung = rec.mesh_descriptors[0]
    assert lung.descriptor == "Lung Neoplasms"
    assert lung.qualifier == "drug therapy"
    # Descriptor has MajorTopicYN="Y", so major_topic should be True
    assert lung.major_topic is True

    humans = rec.mesh_descriptors[1]
    assert humans.major_topic is False


def test_author_orcid_extraction(client: PubMedClient) -> None:
    """ORCID is extracted and normalized from author XML."""
    records = client._parse_efetch_xml(EFETCH_XML)
    rec = records[0]

    # First author has ORCID
    assert rec.authors[0].orcid == "0000-0001-2345-6789"
    # Second author does not
    assert rec.authors[1].orcid is None


def test_medline_indexed_flag(client: PubMedClient) -> None:
    """MEDLINE status is correctly parsed from citation status."""
    records = client._parse_efetch_xml(EFETCH_XML)
    rec = records[0]
    assert rec.medline_indexed is True

    # Test non-MEDLINE status
    non_medline_xml = EFETCH_XML.replace(
        b'Status="MEDLINE"', b'Status="PubMed-not-MEDLINE"'
    )
    records2 = client._parse_efetch_xml(non_medline_xml)
    assert records2[0].medline_indexed is False


def test_raw_xml_preserved(client: PubMedClient) -> None:
    """raw_xml field contains the original article XML."""
    records = client._parse_efetch_xml(EFETCH_XML)
    rec = records[0]

    assert rec.raw_xml is not None
    assert len(rec.raw_xml) > 0
    # The raw XML should contain the article content
    assert "12345678" in rec.raw_xml
    assert "Targeted Therapy" in rec.raw_xml
    assert "PubmedArticle" in rec.raw_xml
