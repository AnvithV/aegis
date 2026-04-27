// ===== Query Request =====

export type Population = "translational" | "drug_discovery" | "clinician";

export interface QueryRequest {
  task_description: string;
  population?: Population;
  mesh_override?: string[];
  k?: number; // default 20, range 5-100
  cutoff_strategy?: string;
}

// ===== Candidate Result (per candidate in ranked list) =====

export interface ScoreComponents {
  R: number; // Recency
  Q: number; // Quality prior
  C: number; // Contextual fit / topical fit
  I: number; // Integrity
}

export interface ScoreVarianceBand {
  low: number;
  high: number;
}

export interface Artifact {
  id: string;
  type: "pmid" | "nct" | "patent" | "grant";
  url: string;
  title: string;
}

export interface Provenance {
  weight_version: string;
  integrity_rule_version: string;
}

export interface CandidateResult {
  uuid: string;
  name: string;
  affiliation: string; // ROR-normalized
  rank: number;
  score: number;
  score_variance_band: ScoreVarianceBand;
  specialty: string;
  identity_linkage_confidence: number;
  score_components: ScoreComponents;
  top_artifacts: Artifact[];
  integrity_disclosures: string[]; // may be empty
  provenance: Provenance;
}

// ===== Query Response =====

export interface QueryResponse {
  id: string;
  task_description: string;
  population?: Population;
  k: number;
  candidates: CandidateResult[];
  created_at: string; // ISO 8601
  mesh_override?: string[];
  cutoff_strategy?: string;
}

// ===== Query List (for history) =====

export interface QuerySummary {
  id: string;
  task_description: string;
  population?: Population;
  k: number;
  result_count: number;
  created_at: string; // ISO 8601
}

export interface QueryListResponse {
  queries: QuerySummary[];
  total: number;
  page: number;
  per_page: number;
}

// ===== Evidence Trail =====

export interface EvidenceTrail {
  candidate_uuid: string;
  candidate_name: string;
  evidence_items: EvidenceItem[];
}

export interface EvidenceItem {
  type: string;
  source: string;
  description: string;
  url?: string;
  date?: string;
  score_contribution?: number;
}

// ===== Feedback =====

export interface FeedbackRequest {
  fleiss_kappa: number; // 0-1
  accept_rate: number; // 0-1
  consensus_rate: number; // 0-1
}

export interface FeedbackResponse {
  task_id: string;
  status: string;
  submitted_at: string;
}
