---
title: Aegis — Phase Plan Index
description: Index of executable phase plans for Aegis, the expert discovery and ranking engine. Each phase is consumable by an AgentTeam (/build_v2). Plans inherit definitions from the program overview.
---

# Aegis — Phase Plan Index

Aegis is the expert discovery and ranking engine for healthcare, biomedical research, and drug-discovery talent. Design system-of-record lives at [`specs/aegis/00-program-overview.md`](../../../specs/aegis/00-program-overview.md). This directory holds the executable phase plans.

## Reading order

1. **Start with the program overview** — `specs/aegis/00-program-overview.md`. Taxonomy, scoring identity, integrity gate, source map, ethics policy, worked examples. All phase plans inherit definitions from it.
2. **Then read the relevant phase plan.** Each plan is self-contained for scope, deliverables, tasks, verification — what an AgentTeam needs to execute.

## Phases

| # | Plan | Duration | Depends on | Deliverable |
|---|---|---|---|---|
| 0 | [`phase-0-foundation.md`](phase-0-foundation.md) | 4 weeks | — | Identity-resolution layer + PubMed/RePORTER/CT.gov ingestion + NSCLC translational seed cohort + archetype validation harness |
| 1 | [`phase-1-scoring.md`](phase-1-scoring.md) | 8 weeks | Phase 0 closed | Full quality prior `Q(c)` + integrity gate `I(c)` + topical fit `T(c, q)` + recency `R(c, q)` + end-to-end `Rank(c, q)` + bootstrap pairwise audit panel + Plackett–Luce weight learning |
| 2 | [`phase-2-multi-population.md`](phase-2-multi-population.md) | 12 weeks | Phase 1 closed | Drug-discovery cohort (USPTO/EPO patents, CPC, ChEMBL) + clinician cohort (NPI, ABMS, hospital tier) + dynamic specialty reassignment (Archetype 2) + cross-population identity merge |
| 3 | [`phase-3-production.md`](phase-3-production.md) | Ongoing (16w cutover) | Phase 2 closed + customer pilot | Customer-facing query API + event-driven integrity ingestion + LLM-backed query expansion + downstream-quality feedback loop + geographic broadening (EPO, ERC, MRC, CIHR, KAKEN, NSFC) + contestability workflow |

## Task counts

| Phase | Core | Observability | Error | Perf | Total |
|---|---:|---:|---:|---:|---:|
| 0 | 10 | 5 | 4 | 3 | **22** |
| 1 | 15 | 5 | 4 | 3 | **27** |
| 2 | 15 | 5 | 4 | 3 | **27** |
| 3 | 12 | 5 | 4 | 3 | **24** |
| | | | | | **100** |

## Exit criteria (top-level)

A phase only closes when its full self-audit checklist passes. Headline gates:

- **Phase 0:** archetypes Dr. A and Dr. B verifiable from the cohort store; ≥80% recall against NSCLC apex list; probabilistic-linker recovery ≥95%; daily incremental ingest <30 min.
- **Phase 1:** archetype Dr. A in top 1% on its query, archetype Dr. D excluded by integrity gate; apex-recall regression ≥80%; ≥500 pairwise judgments collected; Plackett–Luce refit converges with stable CIs.
- **Phase 2:** archetypes Dr. B (industry pivot) and Dr. C (industry-only) hit predicted scoring outcomes; specialty classifier ≥92% held-out accuracy; cross-population identity merge precision ≥99%; per-population audit panels each produce ≥300 pairwise judgments.
- **Phase 3:** customer API live with auth + audit logging; integrity-source latency p99 <6h; downstream-quality feedback flowing from at least one customer pilot; cohort non-US ratio ≥40%; load test sustains 100 qps for 1h within SLO.

## Execution model

Each phase plan is consumable by `/build_v2`:

```
/build_v2 docs/plans/aegis/phase-0-foundation.md
```

The `/build_v2` workflow enforces task ownership, polls task status indefinitely, and reports against the plan's self-audit. When a phase closes per its exit criteria, the next phase unlocks.

## Where things live

```
specs/aegis/
  00-program-overview.md        ← design system-of-record (read first)

docs/plans/aegis/
  README.md                     ← this file
  phase-0-foundation.md
  phase-1-scoring.md
  phase-2-multi-population.md
  phase-3-production.md
```

## Glossary, scoring math, source list

All in the program overview. Do not duplicate definitions into phase plans; reference `specs/aegis/00-program-overview.md` and link by section number (`§3 source map`, `§7 weight vectors`, `§9 scoring math`, `§11 archetypes`, etc.).

## Change control

Changes to taxonomy, scoring identity, integrity-gate rules, source list, weight vectors, or ethics policy must land in the program overview *first*. Phase plans then adopt the change in their next revision. The reverse — letting a phase plan introduce a definition that contradicts the overview — is the failure mode this two-tier structure exists to prevent.
