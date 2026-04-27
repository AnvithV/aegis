-- Per-MeSH-term inverted index: maps MeSH descriptors to candidate UUIDs
-- This powers T(c, q) topic-relevance lookup in Phase 1 scoring
CREATE TABLE IF NOT EXISTS mesh_candidate_index (
    descriptor TEXT NOT NULL,
    qualifier TEXT NOT NULL DEFAULT '',
    major_topic BOOLEAN NOT NULL DEFAULT false,
    candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
    PRIMARY KEY (descriptor, qualifier, candidate_uuid)
);

-- Per-year artifact aggregation: counts artifacts per candidate per year
CREATE TABLE IF NOT EXISTS yearly_artifact_counts (
    candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
    year INTEGER NOT NULL,
    artifact_type TEXT NOT NULL,  -- 'publication', 'grant', 'trial'
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (candidate_uuid, year, artifact_type)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_mesh_descriptor
    ON mesh_candidate_index(descriptor);
CREATE INDEX IF NOT EXISTS idx_artifact_refs_candidate
    ON artifact_refs(candidate_uuid);
CREATE INDEX IF NOT EXISTS idx_artifact_refs_id
    ON artifact_refs(artifact_id);
CREATE INDEX IF NOT EXISTS idx_affiliation_ror
    ON affiliation_history(ror_id);
CREATE INDEX IF NOT EXISTS idx_yearly_candidate
    ON yearly_artifact_counts(candidate_uuid, year);
CREATE INDEX IF NOT EXISTS idx_strong_keys_candidate
    ON strong_keys(candidate_uuid);
