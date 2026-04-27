CREATE TABLE IF NOT EXISTS patent_refs (
    patent_id TEXT NOT NULL,
    candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
    source TEXT NOT NULL,  -- 'uspto' or 'epo'
    family_id TEXT,
    PRIMARY KEY (patent_id, candidate_uuid)
);
CREATE INDEX IF NOT EXISTS idx_patent_refs_candidate ON patent_refs(candidate_uuid);
CREATE INDEX IF NOT EXISTS idx_patent_refs_family ON patent_refs(family_id);
