---
title: Aegis Phase 2 — Multi-Population (Drug Discovery + Clinicians)
description: Extend Aegis from the translational-only Phase 1 cohort to the full three-population platform — adding drug-discovery R&D (USPTO patents, CPC, ChEMBL) and practicing clinicians (NPI, ABMS, hospital tier), plus the dynamic specialty-reassignment classifier that handles industry-pivot archetypes.
---

# Aegis Phase 2 — Multi-Population

For AI: Execute this plan using the executing-plans skill. Mark tasks complete as you go. Stop and verify after each task.

**Created:** 2026-04-24
**Status:** Draft (gated on Phase 1 exit)
**Location:** docs/plans/aegis/phase-2-multi-population.md
**Duration target:** 12 weeks
**Inherits from:** specs/aegis/00-program-overview.md
**Depends on:** docs/plans/aegis/phase-1-scoring.md (must be closed)

## Overview

Phase 2 turns Aegis from a single-specialty engine into the unified three-population platform described in the program overview. Two populations are added: **drug-discovery R&D** (medicinal chemists, structural biologists, DMPK/ADMET, formulation) and **practicing clinicians** (MDs/DOs, surgeons, hospital-based specialists). The shared scoring spine from Phase 1 remains; the new work is in source ingestion, specialty-specific weight vectors, and the dynamic specialty-reassignment classifier.

Phase 2 produces five outcomes:

1. USPTO + EPO patent ingestion at population scale, with inventor-level identity resolution and CPC/IPC + ChEMBL cross-walks for topic-vector construction.
2. NPI Registry + CMS ingestion for the clinician population, with ABMS board certification, state-medical-board action ingestion, and hospital-tier classification.
3. Drug-discovery weight vector and clinician weight vector (with new clinician-specific F7) implemented, calibrated against pairwise audits per population.
4. Dynamic specialty classifier that routes a candidate to the appropriate weight vector based on last-36-month artifact mix, including dynamic reassignment for industry-pivot cases (Archetype 2).
5. Cross-population identity merge: the same person may be a translational PI and a drug-discovery patent inventor; their candidate record is unified, but their scoring uses the appropriate weight vector for the query.

## Prerequisites

- Phase 1 closed: end-to-end ranking for translational cohort, audit panel and Plackett–Luce refit operational, archetype harness passing for Dr. A and Dr. D.
- `specs/aegis/00-program-overview.md` sections referenced: §3 cross-walks, §4 source map, §7 specialty weight vectors, §8 hard-gate (NPI exclusion), §11 archetypes 2 and 3.
- Audit panels recruited for new populations: 5–7 industry medicinal chemists / structural biologists for drug-discovery; 5–7 senior clinicians (radiology, oncology, pathology) for clinician population.

## Core Multi-Population Tasks

### Task 1.1: USPTO PatentsView ingestion

**Description:** Build a typed client for USPTO PatentsView API returning granted patents with patent number, grant date, application date, all inventors with disambiguated IDs (PatentsView provides its own author-disambiguation), all assignees with type (organization vs individual), CPC and IPC classifications, claims (text), abstract, and forward-citation count. Incremental refresh by grant date. Patents are the dominant artifact for medicinal chemists; some have 50+ patents and zero PubMed papers.

**Files:**
- `src/aegis/sources/uspto.py`
- `src/aegis/sources/uspto_test.py`.

**Implementation Notes:**
- PatentsView's inventor disambiguation is a useful prior for our identity resolver but is not a substitute; we cross-validate against ORCID and the PubMed co-author graph.
- Forward-citation count is a quality signal; pull it monthly because it changes.
- Patent maintenance fees (paid at 3.5/7.5/11.5 years post-grant) signal the patent owner's belief in commercial value; ingest fee status when available.

**Verification:**
- Pull all USPTO patents with CPC C07D (heterocyclic chemistry) granted in the last 5 years; count within ±2% of PatentsView UI.
- Inventor-disambiguation IDs link to consistent candidate UUIDs after our identity resolver runs.

**Design Assertions:**
- `UsptoClient.fetch_patents(cpc_codes: list[str], since: date) -> Iterator[PatentRecord]`.
- `PatentRecord.inventors: list[InventorAttribution]` with `disambiguated_id: str`.

### Task 1.2: EPO Espacenet ingestion (international patents)

**Description:** Ingest patents from the European Patent Office's Espacenet via the OPS (Open Patent Services) API, covering EP applications and grants. Many EU-based pharma R&D patents do not file in the US; ignoring EPO produces the geographic bias the program overview §15 explicitly warns against. Incremental by publication date.

**Files:**
- `src/aegis/sources/epo.py`
- `src/aegis/sources/epo_test.py`.

**Implementation Notes:**
- EPO data is sparser on inventor names than USPTO; cross-validate with the Espacenet world bibliographic file.
- Family-of-patents linking: USPTO and EPO patents on the same invention should not both contribute full weight to `v_c`; deduplicate at the family level.

**Verification:**
- Pull ~5,000 EP patents with relevant CPC; family-link rate against USPTO entries ≥60%.

**Design Assertions:**
- `EpoClient.fetch_patents(cpc_codes: list[str], since: date) -> Iterator[PatentRecord]`.

### Task 1.3: CPC/IPC code cross-walk to MeSH

**Description:** Build a cross-walk from CPC/IPC patent classification codes to MeSH descriptors so patent-derived signals enter the same `v_c` topic vector as paper-derived signals. CPC has its own hierarchy (~250K codes vs MeSH's ~30K terms); not all CPC codes have meaningful MeSH equivalents. Maintain a curated mapping for the ~500 most-relevant codes (A61K, A61P, C07D, C12N subclasses) plus an LLM-fallback for tail codes.

**Files:**
- `src/aegis/taxonomy/cpc_mesh_xwalk.py`
- `data/aegis/cpc_mesh_xwalk_v1.yaml` — curated mapping.
- `src/aegis/taxonomy/cpc_mesh_test.py`.

**Implementation Notes:**
- LLM fallback uses constrained generation: given a CPC code description, propose ≤3 MeSH descriptors from the controlled vocabulary; cache outputs.
- Cross-walk is reviewed quarterly by a subject-matter expert.
- A patent contributes to `v_c[mesh]` proportional to the cross-walk weight.

**Verification:**
- Hand-labeled 200 (CPC, MeSH) pairs; cross-walk top-1 ≥85% agreement.
- Patent for known JAK2 inhibitor receives MeSH `JAK2 / antagonists & inhibitors` weight via cross-walk.

**Design Assertions:**
- `CpcMeshXwalk.translate(cpc_code: str) -> list[(MeshDescriptor, float)]`.

### Task 1.4: ChEMBL target cross-walk

**Description:** Cross-walk ChEMBL target IDs to UniProt + MeSH gene/protein/pathway descriptors so chemistry queries ("targeting JAK2," "PI3K-α inhibitor") expand into the same vector space as biological queries. ChEMBL is the EBI bioactivity database; its target taxonomy is the most useful cross-reference for med-chem queries.

**Files:**
- `src/aegis/taxonomy/chembl_xwalk.py`
- `src/aegis/sources/chembl.py` — bulk ingestion.
- `src/aegis/taxonomy/chembl_xwalk_test.py`.

**Implementation Notes:**
- ChEMBL ships a SQLite dump; ingest it once and refresh quarterly.
- Cross-walk is target → list of MeSH descriptors covering the target, its pathway, and its disease associations.

**Verification:**
- Query "JAK2 kinase inhibitor" expands via ChEMBL to MeSH `Janus Kinase 2`, `Janus Kinase Inhibitors`, `Myeloproliferative Disorders`.

**Design Assertions:**
- `ChemblXwalk.target_to_mesh(target_id: str) -> list[MeshDescriptor]`.

### Task 1.5: NPI Registry and CMS ingestion

**Description:** Ingest the National Provider Identifier registry (CMS NPPES bulk file) and the CMS exclusion data (HHS-OIG LEIE — already ingested in Phase 1, cross-referenced here). NPI fields used: NPI number, full name, taxonomy code (specialty), credentials (MD/DO/PhD/etc.), practice address, primary affiliation. The NPPES file is ~1.6M active providers; ingestion is a one-shot bulk + monthly delta.

**Files:**
- `src/aegis/sources/nppes.py`
- `src/aegis/sources/nppes_test.py`.

**Implementation Notes:**
- NPPES taxonomy codes (NUCC) map to ABMS specialties and are used as a pre-filter for clinician cohort assembly.
- The bulk file is ~6 GB; use streaming parsing.
- Practice address is geocoded to enable geographic-relevance queries.

**Verification:**
- Full bulk-file ingest completes in <2 hours; row count matches NPPES published total.
- 1,000 sampled NPIs cross-link to PubMed authors with ≥40% recall (clinicians publish less; this is expected).

**Design Assertions:**
- `NppesClient.bulk_ingest(file_path: Path) -> IngestStats`.
- `Candidate` schema accepts `npi: Optional[str]` as a strong key.

### Task 1.6: State medical board action ingestion

**Description:** Ingest disciplinary actions from state medical boards (license suspension, revocation, restriction, surrender, probation) for the integrity gate. Coverage in Phase 2: top-10 states by physician population (CA, NY, TX, FL, IL, PA, OH, NC, GA, MI), federated by state-board public APIs or scrapers. Phase 3 broadens to all 50 states + territories.

**Files:**
- `src/aegis/sources/state_medical_boards/` — per-state modules.
- `src/aegis/sources/state_medical_boards/registry.py` — federation.
- `src/aegis/sources/state_medical_boards_test.py`.

**Implementation Notes:**
- Each state has a different data format; per-state scrapers/clients are inevitable.
- FSMB (Federation of State Medical Boards) sells aggregated data; Phase 2 builds direct federation; Phase 3 may license FSMB if direct fed becomes too costly.
- Action severity is parsed into a closed enum (revocation > suspension > restriction > probation > public reprimand) and feeds the hard gate.

**Verification:**
- 10-state coverage produces a non-empty action database; planted-test physician with known revocation hits the gate.

**Design Assertions:**
- `StateMedicalBoardRegistry.lookup(npi: str) -> list[BoardAction]`.

### Task 1.7: ABMS board certification ingestion

**Description:** Ingest American Board of Medical Specialties certification status (board, subspecialty, certification date, MOC status) per physician. ABMS provides a paid API (Certification Matters); ingestion uses the licensed feed. Certification data feeds F7 (clinician F-family).

**Files:**
- `src/aegis/sources/abms.py`
- `src/aegis/sources/abms_test.py`.

**Implementation Notes:**
- ABMS data is licensed; ingestion code is generic and supports the alternative AOA (osteopathic) and CMS-published certification cross-references as fallbacks if the ABMS license is not in place.
- Certification + MOC status → F7 sub-score component.

**Verification:**
- Sampled 200 NPIs with known ABMS status; ingestion matches.

**Design Assertions:**
- `AbmsClient.fetch_certification(npi: str) -> AbmsCertification`.

### Task 1.8: Hospital-tier classification (USNWR cross-walk)

**Description:** Cross-walk hospital affiliations (from NPI primary practice address + ROR) to the USNWR Best Hospitals + Best Specialty Hospitals rankings. Tier is one input to F7. The mapping is small (~5,000 ranked hospitals) and updated annually.

**Files:**
- `src/aegis/sources/usnwr.py`
- `data/aegis/hospital_tier_v{year}.yaml` — annual tier list.

**Implementation Notes:**
- USNWR data is publicly browseable but not API-exposed; an annual scrape with manual review is acceptable cadence.
- Specialty rankings (e.g., Cancer at MD Anderson) override overall tier when query specialty matches.

**Verification:**
- 500 sampled NPIs link to a tier with ≥80% non-null rate.

**Design Assertions:**
- `HospitalTier.lookup(ror_id: str, specialty: Optional[str]) -> HospitalTierRank`.

### Task 1.9: ICD-10 / CPT cross-walk for clinicians

**Description:** Cross-walk ICD-10-CM (conditions seen) and CPT (procedures performed) codes to MeSH. Necessary because clinician artifact mix is dominated by claims/coding data, not papers. Phase 2 uses Medicare Provider Utilization & Payment Data (CMS PPSAS) as a public proxy for procedure volume; private-payer claims are out of scope.

**Files:**
- `src/aegis/taxonomy/icd10_mesh.py`
- `src/aegis/taxonomy/cpt_mesh.py`
- `src/aegis/sources/cms_ppsas.py`
- `src/aegis/taxonomy/icd10_cpt_test.py`.

**Implementation Notes:**
- ICD-10 → MeSH cross-walks exist (UMLS provides one); CPT → MeSH is sparser and partially custom.
- Procedure-volume proxies are noisy; we report them with a coverage caveat.

**Verification:**
- Top-coded radiology CPTs map to expected MeSH (e.g., 71250 → `Tomography, X-Ray Computed / methods`).

**Design Assertions:**
- `Icd10MeshXwalk.translate(icd10: str) -> list[MeshDescriptor]`.

### Task 1.10: Drug-discovery weight vector implementation

**Description:** Implement the drug-discovery weight vector `(F1 .15, F2 .05, F3 .15, F4 .05, F5 .50, F6 .10)` in the scoring pipeline. F5 (translational impact) becomes the dominant family for this population — patents granted, FDA submissions, drugs in pipeline. Wire the same `Q(c)` composition with the new weight version.

**Files:**
- `config/aegis/weights/drug_discovery_v1.yaml`
- `src/aegis/scoring/drug_discovery_weights.py`.

**Implementation Notes:**
- F5 in drug-discovery includes the patent signals enabled by Tasks 1.1–1.3; this is where Phase 2's patent ingestion pays off.
- F2 funding has weight 0.05 because industry researchers have minimal NIH funding; we do not penalize them for that.
- F3 leadership in this population is "patent inventorship as lead inventor" + "lead author on conference talks" + (where present) editorial roles.

**Verification:**
- Archetype 3 (Dr. C, comp-chem industry) under drug-discovery weights yields `Q(c) ≈ 0.89 pct` and final `Rank ≈ 0.59`.

**Design Assertions:**
- Weight version `drug_discovery_v1` registered in weight-version table.

### Task 1.11: Clinician weight vector + F7 implementation

**Description:** Implement the clinician weight vector `(F1 .15, F2 .10, F3 .25, F4 .05, F5 .15, F6 .05)` plus F7 = 0.25. F7 is the clinician-specific family: ABMS board certification + MOC status, active license (state board), hospital tier (USNWR), clinical-trial PI roles, procedure-volume proxies. F7 sub-score is itself a weighted composition of these inputs, percentile-calibrated within clinician cohort.

**Files:**
- `config/aegis/weights/clinician_v1.yaml`
- `src/aegis/scoring/f7_clinician.py`
- `src/aegis/scoring/clinician_weights.py`
- `src/aegis/scoring/f7_clinician_test.py`.

**Implementation Notes:**
- F7 is the only place hospital tier feeds; F1–F6 are population-agnostic.
- A licensed but not-board-certified clinician scores lower on F7 but is not gated out (gating is integrity-only).
- Procedure-volume proxies are reported with confidence; many specialties don't have clean public volume data.

**Verification:**
- Distribution of F7 across clinician cohort is uniform (percentile-calibrated).
- Top-decile F7 contains ≥80% of major-academic-center department heads in target specialties.

**Design Assertions:**
- `F7Computer.score(candidate) -> F7Score`.

### Task 1.12: Specialty classifier (artifact-mix-based)

**Description:** Build a classifier that takes a candidate's last-36-month artifact mix (papers, patents, grants, trials, NPI, ABMS, etc.) and returns a probability over specialties: translational, drug-discovery, clinician. Phase 2 implementation is gradient-boosted-trees on hand-crafted features (artifact-type proportions, RCR distribution, NPI presence, patent count, last-author rate, etc.). Default routing is to the highest-probability specialty; below 0.6 confidence triggers ambiguity flag.

**Files:**
- `src/aegis/scoring/specialty_classifier.py`
- `src/aegis/scoring/specialty_classifier_test.py`.

**Implementation Notes:**
- Training labels: hand-curated set of ~500 candidates per specialty (1,500 total); curated by audit panel members.
- Calibration: isotonic regression on probabilities so they're interpretable as confidence.
- Ambiguous candidates are scored under the highest-prob specialty but the result carries a flag.

**Verification:**
- Held-out accuracy ≥92% on hand-curated set.
- Archetype 2 (industry pivot) gets `drug_discovery > translational` with confidence ≥0.7.

**Design Assertions:**
- `SpecialtyClassifier.classify(candidate) -> SpecialtyDistribution`.

### Task 1.13: Dynamic specialty reassignment

**Description:** When a candidate's specialty classification changes (e.g., translational → drug-discovery for the industry-pivot archetype), reassign their weight vector and recompute `Q(c)`. The candidate's identity does not change; only the active specialty annotation does. Reassignment runs nightly during recompute; major changes (>0.3 probability shift) trigger an audit log entry.

**Files:**
- `src/aegis/scoring/specialty_reassignment.py`
- `src/aegis/scoring/specialty_reassignment_test.py`.

**Implementation Notes:**
- Reassignment is the mechanism behind Archetype 2's correct scoring under Phase 2.
- Audit log captures the artifact-mix shift that drove the reclassification — debugging and reviewer-trust depend on this trail.
- A candidate may carry **multiple specialty annotations** with weights — when scoring against a query, the system uses the specialty whose weight vector is most relevant; this is needed for cross-population candidates (the rare clinician-scientist who is also a med-chem patent inventor).

**Verification:**
- Synthetic Dr. B → reassigned from translational to drug-discovery; under correct cohort `Rank ≈ 0.66` (matches §11 prediction).
- Audit log entries are well-formed.

**Design Assertions:**
- `SpecialtyReassigner.reassign_all(cohort) -> ReassignmentReport`.

### Task 1.14: Conference proceedings ingestion

**Description:** Ingest invited talks and named lectureships from major society conferences (ASCO, AACR, ACS, RSNA, ASH, ESMO) for F3 leadership and F4 apex tier. Phase 2 covers the top-3 conferences per specialty; Phase 3 broadens. Many proceedings are PDF-only; ingestion uses LLM-extraction with constrained-output validation against author lists in PubMed.

**Files:**
- `src/aegis/sources/conferences/asco.py`, `acs.py`, `aacr.py`, etc.
- `src/aegis/sources/conferences/llm_extract.py`
- `src/aegis/sources/conferences_test.py`.

**Implementation Notes:**
- LLM extraction is constrained to "extract list of (presenter name, talk type, session title)"; all extractions cross-validated against PubMed/ORCID.
- Named lectureships (e.g., "ASCO Karnofsky Lecture") feed F4; regular invited talks feed F3.

**Verification:**
- 100 sampled talks from ASCO 2024: extraction accuracy ≥90%.

**Design Assertions:**
- `ConferenceIngestor.ingest(year: int, society: str) -> Iterator[TalkRecord]`.

### Task 1.15: Cross-population identity merge + patent-MeSH integration

**Description:** When a single candidate has artifacts in multiple populations (e.g., an MD-PhD with PubMed papers AND patents AND NPI), the candidate record is unified under one UUID. The `v_c` topic vector incorporates papers (PubMed) and patents (USPTO/EPO via CPC cross-walk) in the same space. The candidate's specialty classification can show multiple specialties with weights, and the scoring engine picks the active specialty per query.

**Files:**
- `src/aegis/identity/cross_population_merge.py`
- `src/aegis/scoring/multi_specialty.py`
- `src/aegis/identity/cross_population_test.py`.

**Implementation Notes:**
- Identity merge uses the same Fellegi–Sunter linker from Phase 0, extended with patent-inventor ID and NPI as additional strong-key candidates.
- Where inventor-name on a patent matches a PubMed author with high confidence, the patent's CPC-derived MeSH contributions add to the candidate's `v_c`.

**Verification:**
- Planted MD-PhD with patents + papers + NPI: single UUID, multi-specialty annotation, scoring picks correct specialty per query.

**Design Assertions:**
- `Candidate.specialty_distribution: dict[Specialty, float]`.

## Observability and Governance Tasks

### Task 2.1: Specialty-distribution dashboard

**Description:** Cohort dashboards showing specialty distribution, multi-specialty candidates, and reassignment rates. Phase 2 expects roughly 60% translational / 25% drug-discovery / 15% clinician on the seed expansion; large deviations are diagnostic.

**Files:**
- `src/aegis/observability/specialty_dist.py`
- Dashboards.

**Implementation Notes:**
- Per-specialty cohort sizes inform whether F-family percentile calibration has enough population.
- Multi-specialty candidates surface as a separate count with their weight distribution.

**Verification:**
- Dashboard renders with expected distributions on the test corpus.

### Task 2.2: Specialty-reassignment rate and stability

**Description:** Track how often candidates are reassigned across specialties and the magnitude of probability changes. High churn signals classifier instability; we want <5% of candidates reassigned per nightly run on a steady-state cohort.

**Files:**
- `src/aegis/observability/reassignment_metrics.py`.

**Implementation Notes:**
- Reassignment rate over time, per-source-of-change attribution (new artifacts vs classifier drift).
- Alerts on sudden spikes.

**Verification:**
- Synthetic stable cohort: <1% nightly reassignment.
- Synthetic injected drift: alert fires.

### Task 2.3: Patent-vs-paper signal balance dashboard

**Description:** For each drug-discovery candidate, show the relative contribution of patents vs papers vs trials to `v_c` and to `Q(c)`. The signal balance reveals whether the cross-walk weights are calibrated; over-reliance on patents (or under-counting them) shows up here.

**Files:**
- `src/aegis/observability/signal_balance.py`.

**Implementation Notes:**
- Per-candidate breakdown in evidence trail; aggregate view in dashboard.
- Alerts on cohort-level shifts (e.g., patents suddenly driving 90% of `v_c` mass would indicate an ingestion bug).

**Verification:**
- Archetype 3 (Dr. C) shows ≥70% of `v_c` mass from patents (expected for industry comp-chem).

### Task 2.4: Clinician coverage diagnostics

**Description:** Coverage diagnostics specific to the clinician cohort: % NPIs cross-linked to a Candidate UUID, % with ABMS data, % with state-medical-board data, % with hospital-tier mapping, % with publications. Coverage caveats per cohort are reported alongside scores per program overview §12.

**Files:**
- `src/aegis/observability/clinician_coverage.py`.

**Implementation Notes:**
- Clinicians often have no PubMed publications; coverage report distinguishes "missing data" from "this dimension genuinely doesn't apply."
- 10-state board coverage gap is documented and the dashboard shows it explicitly.

**Verification:**
- Dashboard renders; gap states are flagged.

### Task 2.5: Cross-population identity merge accuracy

**Description:** Track precision and recall of cross-population identity merging via held-out test set: known MD-PhDs with PubMed + patents + NPI, plus deliberate adversarial cases (different people with similar names). Over-merging is more dangerous than under-merging in this product (false unification of identities is contestable).

**Files:**
- `src/aegis/observability/merge_accuracy.py`
- `tests/regression/test_cross_pop_merge.py`.

**Implementation Notes:**
- Held-out test grows over time with HITL-confirmed cases.
- Precision target ≥99% on auto-merged; recall target ≥85%.

**Verification:**
- Held-out set passes precision threshold.

## Error Handling Tasks

### Task 3.1: Specialty-classifier ambiguity

**Description:** Below 0.6 specialty-classifier confidence, score the candidate under the top-2 specialty weight vectors and report both ranks; flag the result as multi-specialty-ambiguous so the customer can inspect. Above 0.6, single-specialty scoring with the ambiguity flag suppressed.

**Files:**
- `src/aegis/scoring/ambiguity_handling.py`.

**Implementation Notes:**
- Top-2 ranking is for transparency, not consensus; we don't average. The customer chooses which is more relevant for their query.
- Ambiguity flag persists across recomputation until classifier confidence rises.

**Verification:**
- Synthetic ambiguous candidate gets dual-rank output; high-confidence candidate gets single-rank output.

### Task 3.2: Patent inventor disambiguation failures

**Description:** When PatentsView's inventor-disambiguation conflicts with our Fellegi–Sunter output (e.g., USPTO splits one inventor across two IDs, or merges two different inventors), surface the conflict to the HITL queue and treat the patent as ambiguously-attributed (excluded from `v_c` until resolved).

**Files:**
- `src/aegis/identity/patent_conflicts.py`.

**Implementation Notes:**
- Patent inventor disambiguation is genuinely hard; we expect ~5% conflict rate.
- Excluded patents do not silently degrade `v_c`; coverage diagnostics report them.

**Verification:**
- Synthetic conflict surfaces in HITL queue; resolution restores patent attribution.

### Task 3.3: NPI ↔ PubMed name-match low confidence

**Description:** Many physicians publish under variant names (married name, middle initial inconsistent, professional vs full name). When NPI ↔ PubMed match confidence is between 0.5 and 0.95, queue for HITL; never auto-link below 0.95 because mis-attribution at the clinician level (assigning a senior radiologist's NPI to the wrong author) is a high-impact error.

**Files:**
- `src/aegis/identity/npi_pubmed_match.py`.

**Implementation Notes:**
- Higher threshold than other strong-key links because the integrity gate uses NPI for state-board action lookup; mis-attribution can wrongly hard-zero a candidate.
- Reviewer sees specialty + practice address + author affiliation; specialty mismatch is a strong rejection signal.

**Verification:**
- 200 sampled physician-author cases: HITL queue catches all mis-matches.

### Task 3.4: Conference abstract parsing failures

**Description:** Conference proceedings PDFs are heterogeneous; extraction will fail on some sources. When extraction fails, log the failure with source URL and skip; do not block ingestion. Quarterly review of failure rates per source informs whether we replace the parser or drop the source.

**Files:**
- `src/aegis/sources/conferences/failure_log.py`.

**Implementation Notes:**
- Failure log feeds back into the LLM extraction prompt-engineering review.
- Per-conference success rate tracked.

**Verification:**
- Synthetic broken PDF logs a failure and pipeline proceeds.

## Performance and Scale Tasks

### Task 4.1: Patent ingestion volume

**Description:** USPTO + EPO together yield ~10M relevant patents over the last 30 years (filtered by relevant CPC). Ingestion must batch, parallelize, and complete a full historical pull in <72 hours on a single machine. Incremental refresh is <30 min daily.

**Files:**
- `src/aegis/sources/uspto_bulk.py`
- `src/aegis/sources/epo_bulk.py`.

**Implementation Notes:**
- USPTO bulk dumps available via Google Cloud and Bulk Data Storage System; preferable to API for historical pull.
- Full historical pull is one-time; incremental is steady-state.

**Verification:**
- Full historical pull completes within budget.
- Daily incremental <30 min.

### Task 4.2: Clinician corpus scale

**Description:** NPPES is ~1.6M active providers; only a subset (~200K) will be relevant to specialty queries we serve. Optimize: build a per-specialty inverted index keyed by NUCC taxonomy code, so queries don't scan all 1.6M providers.

**Files:**
- `src/aegis/storage/clinician_index.py`.

**Implementation Notes:**
- Index is rebuilt weekly on monthly NPPES delta; per-specialty scan is then O(specialty cohort size).
- Geographic indexing layered on top for locality-aware queries.

**Verification:**
- Specialty-scoped query lookup p95 <100ms.

### Task 4.3: CPC cross-walk caching

**Description:** Cache CPC → MeSH cross-walk lookups; the LLM-fallback path is too slow per-patent if uncached. Cache invalidation on cross-walk version bump (quarterly).

**Files:**
- `src/aegis/taxonomy/cpc_xwalk_cache.py`.

**Implementation Notes:**
- Cache backend: SQLite local; production: Redis or similar.
- Cache hit rate target ≥99% on warmed cohort.

**Verification:**
- Warm cache: cross-walk lookup p99 <1ms.

## Testing

- Unit tests on every new module; coverage ≥85% on new code.
- Archetype regression: Dr. B (Phase 2 reassignment) and Dr. C (Phase 2 industry-only) hit predicted scoring outcomes from §11.
- Specialty-classifier held-out accuracy ≥92%.
- Cross-population identity merge precision ≥99%.
- Apex-list recall regression broadened to drug-discovery (FDA Innovator awardees, Pharmaceutical Research and Manufacturers of America Champions, ACS Heroes of Chemistry) and clinician (USNWR Top Doctors lists, AMA Distinguished Service awards) — ≥70% recall is the Phase 2 floor (these lists are noisier than translational).

## Rollback Plan

Phase 2 changes are additive: the translational cohort and Phase 1 scoring are unchanged. New populations can be disabled via config without affecting existing behavior. Specialty reassignment can be turned off, falling back to static specialty annotation per candidate. Patent ingestion can be paused per-source. The integrity gate remains operational throughout any Phase 2 rollback.

## Self-Audit

- Core multi-population tasks: 15
- Observability and governance tasks: 5
- Error handling tasks: 4
- Performance and scale tasks: 3
- Total tasks: 27
- Tasks with explicit file targets: 27
- Tasks with verification steps: 27
- Tasks with design assertions: 15 (core tasks)
- Phase 2 closes when: (1) Archetypes 2 and 3 from §11 hit predicted scoring outcomes; (2) specialty classifier ≥92% held-out accuracy; (3) cross-population identity merge precision ≥99%; (4) drug-discovery and clinician audit panels each produce ≥300 pairwise judgments and Plackett–Luce refits converge with stable CIs; (5) full population coverage diagnostics published.
