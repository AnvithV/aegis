// ===== Query Request =====

export type Population = "translational" | "drug_discovery" | "clinician";

export interface QueryRequest {
  task_description: string;
  population?: Population;
  mesh_override?: string[];
  k?: number; // default 20, range 5-100
  cutoff_strategy?: string;
  query_type_override?: string;
}

// ===== Candidate Result (per candidate in ranked list) =====

export interface ScoreComponents {
  R: number; // Recency
  Q: number; // Quality prior
  C: number; // Contextual fit / topical fit
  I: number; // Integrity
  f1_rcr?: number;
  f2_funding?: number;
  f3_leadership?: number;
  f4_apex?: number;
  f5_translational?: number;
  f6_lineage?: number;
  f7_clinician?: number;
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
  source_badges?: string[];
  has_notes?: boolean;
  shortlisted_by?: string[];
  openalex_concepts?: string[];
  contact_email?: string | null;
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

export interface FeedbackCandidate {
  candidate_uuid: string;
  rank: number;
  quality_prior_score: number;
  topical_fit_score: number;
  recency_score: number;
}

export interface FeedbackRequest {
  query_specialty: string;
  query_mesh_terms: string[];
  candidates: FeedbackCandidate[];
  fleiss_kappa: number; // 0-1
  accept_rate: number; // 0-1
  consensus_rate: number; // 0-1
}

export interface FeedbackResponse {
  task_id: string;
  status: string;
  submitted_at: string;
}

// ===== Query Type Classification =====

export type QueryType = "basic_research" | "drug_discovery" | "clinical_trial_pi" | "policy_epi";

export interface ClassifyResponse {
  query_type: QueryType;
  confidence: number;
  keyword_matches: string[];
  weights: Record<string, number>;
  exponents: Record<string, number>;
}

// ===== SSE Events =====

export interface SourceProgressEvent {
  source_name: string;
  status: "pending" | "fetching" | "complete" | "failed";
  record_count: number;
  latency_ms: number;
  error: string | null;
}

export interface SSECandidateEvent {
  rank: number;
  uuid: string;
  name: string;
  score: number;
}

// ===== F1-F7 Scores =====

export interface F1F7Scores {
  f1_rcr: number;
  f2_funding: number;
  f3_leadership: number;
  f4_apex: number;
  f5_translational: number;
  f6_lineage: number;
  f7_clinician?: number;
}

// ===== Shortlists =====

export interface Shortlist {
  id: string;
  name: string;
  description: string | null;
  created_by: string;
  created_at: string;
  member_count?: number;
}

export interface ShortlistMember {
  candidate_uuid: string;
  candidate_name?: string;
  added_at: string;
  added_by: string;
}

// ===== Notes =====

export interface CandidateNote {
  id: string;
  candidate_uuid: string;
  author: string;
  content: string;
  created_at: string;
  updated_at: string;
}

// ===== Candidate Profile =====

export interface CandidateProfile {
  uuid: string;
  name: string;
  affiliation: string;
  country: string | null;
  score_history: Array<{ query_id: string; score: number; rank: number; date: string }>;
  publications: number;
  grants: number;
  trials: number;
  patents: number;
  integrity_status: string;
  f1_f7_scores: F1F7Scores;
}

// ===== Jobs =====

export type JobStatus = "in_progress" | "complete" | "failed" | "cancelled";

export interface JobRecord {
  id: string;
  query_text: string;
  status: JobStatus;
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  source_count: number | null;
  candidate_count: number | null;
  created_by: string;
}

export interface JobListResponse {
  jobs: JobRecord[];
  total: number;
  page: number;
  per_page: number;
}
