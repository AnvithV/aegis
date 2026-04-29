"""Seed the DuckDB with 15 demo researchers across 5 specialties."""

from __future__ import annotations

from datetime import UTC, date, datetime

from aegis.storage.candidate_store import CandidateStore
from aegis.storage.schema import AffiliationSpan, ArtifactRefBundle, Candidate, MeshDescriptor

RESEARCHERS: list[dict] = [
    # ── Oncology ─────────────────────────────────────────────────────────────
    {
        "uuid": "onco-001-sarah-chen",
        "strong_keys": {"orcid": "0000-0001-1001-0001", "era_commons": "SCHEN01"},
        "name_variants": ["Sarah Chen", "S. Chen", "Chen, Sarah"],
        "affiliation": ("Memorial Sloan Kettering Cancer Center", "US"),
        "pmids": ["38001122", "37889900", "37654321", "36998877", "36543210",
                  "35987654", "35123456", "34876543"],
        "grant_ids": ["R01CA234567", "P30CA008748"],
        "mesh_descriptors": [
            ("Neoplasms", True), ("Antineoplastic Agents", True),
            ("Drug Resistance, Neoplasm", False), ("Tumor Microenvironment", False),
            ("Immunotherapy", True), ("Biomarkers, Tumor", False),
        ],
        "evidence_trail": [
            "12 publications on targeted oncology therapies indexed in PubMed",
            "Principal investigator on NCI R01 studying drug resistance mechanisms",
            "h-index 28 with 3,200+ citations in oncology literature",
        ],
        "linkage_confidence": 0.97,
    },
    {
        "uuid": "onco-002-michael-rodriguez",
        "strong_keys": {"orcid": "0000-0001-1002-0002", "era_commons": "MRODRIGUEZ02"},
        "name_variants": ["Michael Rodriguez", "M. Rodriguez", "Rodriguez, Michael A."],
        "affiliation": ("MD Anderson Cancer Center", "US"),
        "pmids": ["38201234", "37901234", "37701234", "37501234", "37301234",
                  "37101234", "36901234", "36701234", "36501234", "36301234"],
        "grant_ids": ["R01CA198765", "K08CA210034"],
        "mesh_descriptors": [
            ("Lung Neoplasms", True), ("Carcinoma, Non-Small-Cell Lung", True),
            ("EGFR protein, human", False), ("Mutation", False),
            ("Clinical Trials as Topic", False), ("Survival Analysis", True),
        ],
        "evidence_trail": [
            "Specialist in non-small cell lung cancer molecular targeting",
            "Led 4 Phase II clinical trials in precision oncology",
            "15+ peer-reviewed publications in JCO and NEJM",
        ],
        "linkage_confidence": 0.95,
    },
    {
        "uuid": "onco-003-emma-blackwood",
        "strong_keys": {"orcid": "0000-0001-1003-0003"},
        "name_variants": ["Emma Blackwood", "E. Blackwood", "Blackwood, Emma R."],
        "affiliation": ("Cancer Research UK Cambridge Institute", "GB"),
        "pmids": ["38101111", "37801111", "37501111", "37201111", "36901111",
                  "36601111"],
        "grant_ids": ["CRUK-A12345"],
        "mesh_descriptors": [
            ("Breast Neoplasms", True), ("BRCA1 Protein", True),
            ("DNA Repair", False), ("Poly(ADP-ribose) Polymerase Inhibitors", True),
            ("Genomic Instability", False),
        ],
        "evidence_trail": [
            "CRUK-funded researcher specializing in BRCA-related breast cancer",
            "Co-author on landmark PARP inhibitor mechanism papers",
        ],
        "linkage_confidence": 0.93,
    },
    # ── Cardiology ────────────────────────────────────────────────────────────
    {
        "uuid": "card-001-james-hartley",
        "strong_keys": {"orcid": "0000-0002-2001-0001", "npi": "1234567890"},
        "name_variants": ["James Hartley", "J. Hartley", "Hartley, James T."],
        "affiliation": ("Cleveland Clinic", "US"),
        "pmids": ["38211100", "37811100", "37411100", "37011100", "36611100",
                  "36211100", "35811100", "35411100", "35011100"],
        "grant_ids": ["R01HL134567", "K23HL110234"],
        "mesh_descriptors": [
            ("Heart Failure", True), ("Cardiac Output", False),
            ("Ventricular Dysfunction, Left", True), ("Natriuretic Peptide, Brain", False),
            ("Cardiomyopathies", True), ("Echocardiography", False),
        ],
        "evidence_trail": [
            "NHLBI-funded investigator in heart failure biomarkers",
            "9 high-impact publications in JACC and Circulation",
            "Active clinical practice and NPI-registered cardiologist",
        ],
        "linkage_confidence": 0.98,
    },
    {
        "uuid": "card-002-priya-mehta",
        "strong_keys": {"orcid": "0000-0002-2002-0002", "npi": "2345678901"},
        "name_variants": ["Priya Mehta", "P. Mehta", "Mehta, Priya S."],
        "affiliation": ("Brigham and Women's Hospital", "US"),
        "pmids": ["38312200", "37912200", "37512200", "37112200", "36712200",
                  "36312200", "35912200", "35512200", "35112200", "34712200",
                  "34312200"],
        "grant_ids": ["R01HL143210", "T32HL007604"],
        "mesh_descriptors": [
            ("Atrial Fibrillation", True), ("Anti-Arrhythmia Agents", True),
            ("Stroke", False), ("Risk Factors", False),
            ("Anticoagulants", True), ("Thromboembolism", False),
        ],
        "evidence_trail": [
            "Researcher in atrial fibrillation stroke prevention strategies",
            "11 publications covering anticoagulation in AF populations",
            "NPI registered, active clinician-researcher",
        ],
        "linkage_confidence": 0.96,
    },
    {
        "uuid": "card-003-thomas-brennan",
        "strong_keys": {"orcid": "0000-0002-2003-0003"},
        "name_variants": ["Thomas Brennan", "T. Brennan", "Brennan, Thomas J."],
        "affiliation": ("University of Oxford", "GB"),
        "pmids": ["38213300", "37813300", "37413300", "37013300", "36613300"],
        "grant_ids": ["WT223456MF"],
        "mesh_descriptors": [
            ("Coronary Artery Disease", True), ("Atherosclerosis", True),
            ("Lipids", False), ("Inflammation", False),
            ("Plaque, Atherosclerotic", True),
        ],
        "evidence_trail": [
            "Wellcome Trust-funded investigator studying coronary atherosclerosis",
            "5 publications in European Heart Journal and JACC",
        ],
        "linkage_confidence": 0.91,
    },
    # ── Genomics ──────────────────────────────────────────────────────────────
    {
        "uuid": "geno-001-yuki-tanaka",
        "strong_keys": {"orcid": "0000-0003-3001-0001", "era_commons": "YTANAKA01"},
        "name_variants": ["Yuki Tanaka", "Y. Tanaka", "Tanaka, Yuki"],
        "affiliation": ("Broad Institute of MIT and Harvard", "US"),
        "pmids": ["38114400", "37814400", "37514400", "37214400", "36914400",
                  "36614400", "36314400", "36014400", "35714400", "35414400",
                  "35114400", "34814400"],
        "grant_ids": ["R01HG010234", "U01HG009080"],
        "mesh_descriptors": [
            ("Genomics", True), ("Genome-Wide Association Study", True),
            ("Single Nucleotide Polymorphism", False), ("Whole Genome Sequencing", True),
            ("Gene Expression", False), ("Computational Biology", False),
        ],
        "evidence_trail": [
            "NHGRI-funded researcher in population genomics and GWAS methods",
            "12 publications including Nature Genetics and Cell",
            "Developed widely used open-source GWAS tools",
        ],
        "linkage_confidence": 0.97,
    },
    {
        "uuid": "geno-002-ana-kowalski",
        "strong_keys": {"orcid": "0000-0003-3002-0002"},
        "name_variants": ["Ana Kowalski", "A. Kowalski", "Kowalski, Ana M."],
        "affiliation": ("Wellcome Sanger Institute", "GB"),
        "pmids": ["38215500", "37815500", "37415500", "37015500", "36615500",
                  "36215500", "35815500"],
        "grant_ids": ["WT223891EF"],
        "mesh_descriptors": [
            ("Exome Sequencing", True), ("Rare Diseases", True),
            ("Genetic Variation", False), ("Databases, Genetic", False),
            ("Phenotype", False), ("Genotype", False),
        ],
        "evidence_trail": [
            "Wellcome Sanger researcher focused on rare disease genomics",
            "Contributor to gnomAD exome database consortium",
            "7 publications in Nature Medicine and American Journal of Human Genetics",
        ],
        "linkage_confidence": 0.94,
    },
    {
        "uuid": "geno-003-rajiv-patel",
        "strong_keys": {"orcid": "0000-0003-3003-0003", "era_commons": "RPATEL03"},
        "name_variants": ["Rajiv Patel", "R. Patel", "Patel, Rajiv K."],
        "affiliation": ("Stanford University", "US"),
        "pmids": ["38116600", "37816600", "37516600", "37216600", "36916600",
                  "36616600", "36316600", "36016600", "35716600"],
        "grant_ids": ["R01HG011345", "DP1HG010000"],
        "mesh_descriptors": [
            ("Epigenomics", True), ("DNA Methylation", True),
            ("Chromatin", False), ("Gene Regulatory Networks", True),
            ("Transcription Factors", False), ("CRISPR-Cas Systems", False),
        ],
        "evidence_trail": [
            "NIH DP1 Pioneer Award recipient in epigenomics",
            "9 publications including Science and Nature",
            "Stanford ENCODE project lead contributor",
        ],
        "linkage_confidence": 0.96,
    },
    # ── Drug Discovery ────────────────────────────────────────────────────────
    {
        "uuid": "drug-001-lisa-zhang",
        "strong_keys": {"orcid": "0000-0004-4001-0001"},
        "name_variants": ["Lisa Zhang", "L. Zhang", "Zhang, Lisa X."],
        "affiliation": ("Genentech", "US"),
        "pmids": ["38217700", "37817700", "37417700", "37017700", "36617700",
                  "36217700", "35817700", "35417700", "35017700", "34617700",
                  "34217700", "33817700", "33417700", "33017700"],
        "grant_ids": ["R&D-GNE-2023-01"],
        "mesh_descriptors": [
            ("Drug Discovery", True), ("Molecular Targeted Therapy", True),
            ("Protein Kinase Inhibitors", True), ("Structure-Activity Relationship", False),
            ("Drug Design", False), ("High-Throughput Screening Assays", False),
        ],
        "evidence_trail": [
            "14 publications on kinase inhibitor drug discovery at Genentech",
            "Named inventor on 3 US patents for oncology small molecules",
            "Contributed to 2 FDA-approved targeted therapies",
        ],
        "linkage_confidence": 0.92,
    },
    {
        "uuid": "drug-002-david-okonkwo",
        "strong_keys": {"orcid": "0000-0004-4002-0002"},
        "name_variants": ["David Okonkwo", "D. Okonkwo", "Okonkwo, David C."],
        "affiliation": ("Novartis Institutes for BioMedical Research", "CH"),
        "pmids": ["38118800", "37818800", "37518800", "37218800", "36918800",
                  "36618800", "36318800", "36018800"],
        "grant_ids": ["NIBR-2023-ONC-45"],
        "mesh_descriptors": [
            ("Drug Discovery", True), ("Pharmacology", False),
            ("Proteomics", True), ("Target Discovery", False),
            ("Mass Spectrometry", False), ("Protein Binding", False),
        ],
        "evidence_trail": [
            "Novartis lead scientist in chemoproteomics-based target ID",
            "8 publications on proteomics-driven drug target discovery",
            "Co-inventor on 2 patent applications for novel oncology targets",
        ],
        "linkage_confidence": 0.90,
    },
    {
        "uuid": "drug-003-maria-santos",
        "strong_keys": {"orcid": "0000-0004-4003-0003"},
        "name_variants": ["Maria Santos", "M. Santos", "Santos, Maria L."],
        "affiliation": ("AstraZeneca", "GB"),
        "pmids": ["38219900", "37819900", "37419900", "37019900", "36619900",
                  "36219900", "35819900", "35419900", "35019900", "34619900",
                  "34219900"],
        "grant_ids": ["AZ-IMED-2023-01", "BB/T013923/1"],
        "mesh_descriptors": [
            ("ADME", True), ("Drug Metabolism", True),
            ("Cytochrome P-450 Enzyme System", False), ("Pharmacokinetics", True),
            ("Biological Availability", False), ("Drug Interactions", False),
        ],
        "evidence_trail": [
            "AZ researcher in ADMET profiling and lead optimization",
            "11 publications on drug metabolism and PK/PD modelling",
            "BBSRC co-funded academic-industry collaboration lead",
        ],
        "linkage_confidence": 0.93,
    },
    # ── Biostatistics ─────────────────────────────────────────────────────────
    {
        "uuid": "stat-001-robert-thompson",
        "strong_keys": {"orcid": "0000-0005-5001-0001", "era_commons": "RTHOMPSON01"},
        "name_variants": ["Robert Thompson", "R. Thompson", "Thompson, Robert B."],
        "affiliation": ("Harvard T.H. Chan School of Public Health", "US"),
        "pmids": ["38221010", "37821010", "37421010", "37021010", "36621010",
                  "36221010", "35821010", "35421010", "35021010", "34621010",
                  "34221010", "33821010", "33421010"],
        "grant_ids": ["R01GM134890", "U01AI138907"],
        "mesh_descriptors": [
            ("Biostatistics", True), ("Clinical Trials as Topic", True),
            ("Adaptive Clinical Trials as Topic", False), ("Sample Size", False),
            ("Survival Analysis", True), ("Models, Statistical", False),
        ],
        "evidence_trail": [
            "NIH-funded biostatistician specializing in adaptive trial design",
            "13 publications in Statistics in Medicine and JASA",
            "Statistical consultant to 5 FDA NDA submissions",
        ],
        "linkage_confidence": 0.99,
    },
    {
        "uuid": "stat-002-aiko-yamamoto",
        "strong_keys": {"orcid": "0000-0005-5002-0002"},
        "name_variants": ["Aiko Yamamoto", "A. Yamamoto", "Yamamoto, Aiko"],
        "affiliation": ("University of Tokyo", "JP"),
        "pmids": ["38122020", "37822020", "37522020", "37222020", "36922020",
                  "36622020", "36322020"],
        "grant_ids": ["KAKENHI-21H02748"],
        "mesh_descriptors": [
            ("Biometry", True), ("Bayes Theorem", True),
            ("Markov Chains", False), ("Meta-Analysis as Topic", True),
            ("Statistical Models", False),
        ],
        "evidence_trail": [
            "KAKENHI-funded researcher in Bayesian methods for clinical evidence synthesis",
            "7 publications in Biometrics and Pharmaceutical Statistics",
        ],
        "linkage_confidence": 0.91,
    },
    {
        "uuid": "stat-003-klaus-weber",
        "strong_keys": {"orcid": "0000-0005-5003-0003"},
        "name_variants": ["Klaus Weber", "K. Weber", "Weber, Klaus H."],
        "affiliation": ("Heidelberg University", "DE"),
        "pmids": ["38223030", "37823030", "37423030", "37023030", "36623030",
                  "36223030", "35823030", "35423030"],
        "grant_ids": ["DFG-WE5678/3-1"],
        "mesh_descriptors": [
            ("Statistics as Topic", True), ("Missing Data", True),
            ("Propensity Score", True), ("Epidemiologic Methods", False),
            ("Confounding Factors, Epidemiologic", False),
        ],
        "evidence_trail": [
            "DFG-funded statistician specialising in causal inference and missing data",
            "8 publications on propensity score methods in pharmacoepidemiology",
        ],
        "linkage_confidence": 0.92,
    },
]


def seed() -> None:
    store = CandidateStore("aegis.duckdb")
    now = datetime.now(UTC)

    for r in RESEARCHERS:
        aff_name, country = r["affiliation"]
        candidate = Candidate(
            uuid=r["uuid"],
            strong_keys=r["strong_keys"],
            name_variants=r["name_variants"],
            affiliations=[
                AffiliationSpan(
                    ror_id=None,
                    canonical_name=aff_name,
                    raw_string=aff_name,
                    country=country,
                    confidence=0.95,
                    start_date=date(2018, 1, 1),
                    end_date=None,
                )
            ],
            artifact_refs=ArtifactRefBundle(
                pmids=r["pmids"],
                nct_ids=[],
                grant_ids=r["grant_ids"],
                patent_ids=[],
            ),
            linkage_confidence=r["linkage_confidence"],
            evidence_trail=r["evidence_trail"],
            last_updated_per_source={"pubmed": now},
            mesh_descriptors=[
                MeshDescriptor(descriptor=d, qualifier=None, major_topic=major)
                for d, major in r["mesh_descriptors"]
            ],
        )
        store.upsert(candidate)

        # Also insert into mesh_candidate_index for each MeSH descriptor
        for descriptor, _major in r["mesh_descriptors"]:
            try:
                store._conn.execute(
                    """
                    INSERT INTO mesh_candidate_index (mesh_descriptor, candidate_uuid, score)
                    VALUES (?, ?, ?)
                    ON CONFLICT (mesh_descriptor, candidate_uuid) DO UPDATE SET
                        score = excluded.score
                    """,
                    [descriptor, r["uuid"], 1.0 if _major else 0.6],
                )
            except Exception:
                # Table may not exist in all migration versions — silently skip
                pass

        print(f"  Upserted: {r['name_variants'][0]} ({r['uuid']})")

    total = store.count()
    store.close()
    print(f"\nDone. Total candidates in DB: {total}")


if __name__ == "__main__":
    seed()
