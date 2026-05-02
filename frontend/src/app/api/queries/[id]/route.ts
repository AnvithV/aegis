import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";
import type { CandidateResult } from "@/types/api";

// Backend wire format — not exported; only used for transformation here
interface BackendArtifact {
  artifact_type: string;
  identifier: string;
  title: string;
  url: string;
  contribution_score: number;
}

interface BackendVarianceBand {
  low: number;
  high: number;
  median: number;
}

interface BackendIntegrityDisclosure {
  discount_type: string;
  factor: number;
  detail: string;
}

interface BackendCandidate {
  rank: number;
  candidate_uuid: string;
  candidate_name: string;
  affiliation: string;
  affiliation_country: string | null;
  score: number;
  component_scores: {
    quality_prior: number;
    topical_fit: number;
    recency: number;
    integrity: number;
    f1_rcr?: number;
    f2_funding?: number;
    f3_leadership?: number;
    f4_apex?: number;
    f5_translational?: number;
    f6_lineage?: number;
    f7_clinician?: number;
  };
  top_artifacts: BackendArtifact[];
  linkage_confidence: number;
  variance_band: BackendVarianceBand | null;
  integrity_disclosures: BackendIntegrityDisclosure[];
  specialty: string | null;
  evidence_trail: string[];
  source_badges?: string[];
  openalex_concepts?: string[];
  contact_email?: string | null;
}

interface BackendQueryResponse {
  id: string;
  task_description: string;
  population: string | null;
  k: number;
  candidates: BackendCandidate[];
  created_at: string;
  mesh_override: string[] | null;
  cutoff_strategy: string | null;
  result_count: number;
  query_type?: string;
  weight_vector_name?: string;
}

function transformCandidate(c: BackendCandidate): CandidateResult {
  return {
    uuid: c.candidate_uuid,
    name: c.candidate_name,
    affiliation: c.affiliation ?? "",
    rank: c.rank,
    score: c.score,
    specialty: c.specialty ?? "Researcher",
    identity_linkage_confidence: c.linkage_confidence,
    score_components: {
      R: c.component_scores?.recency ?? 0,
      Q: c.component_scores?.quality_prior ?? 0,
      C: c.component_scores?.topical_fit ?? 0,
      I: c.component_scores?.integrity ?? 0,
      f1_rcr: c.component_scores?.f1_rcr,
      f2_funding: c.component_scores?.f2_funding,
      f3_leadership: c.component_scores?.f3_leadership,
      f4_apex: c.component_scores?.f4_apex,
      f5_translational: c.component_scores?.f5_translational,
      f6_lineage: c.component_scores?.f6_lineage,
      f7_clinician: c.component_scores?.f7_clinician,
    },
    score_variance_band: c.variance_band
      ? { low: c.variance_band.low, high: c.variance_band.high }
      : {
          low: parseFloat((c.score * 0.88).toFixed(3)),
          high: parseFloat((c.score * 1.12).toFixed(3)),
        },
    top_artifacts: (c.top_artifacts ?? []).map((a) => ({
      id: a.identifier,
      type: a.artifact_type as CandidateResult["top_artifacts"][number]["type"],
      url: a.url,
      title: a.title,
    })),
    integrity_disclosures: (c.integrity_disclosures ?? []).map(
      (d) => d.detail ?? ""
    ),
    provenance: { weight_version: "1", integrity_rule_version: "1.0.0" },
    source_badges: c.source_badges,
    openalex_concepts: c.openalex_concepts,
    contact_email: c.contact_email ?? null,
  };
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const data = await apiFetch<BackendQueryResponse>(`/v1/queries/${id}`);
    return NextResponse.json({
      id: data.id,
      task_description: data.task_description,
      population: data.population,
      k: data.k,
      candidates: (data.candidates ?? []).map(transformCandidate),
      created_at: data.created_at,
      mesh_override: data.mesh_override,
      cutoff_strategy: data.cutoff_strategy,
      query_type: data.query_type,
      weight_vector_name: data.weight_vector_name,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
