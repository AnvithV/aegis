CREATE TABLE IF NOT EXISTS grant_refs (
    grant_reference TEXT NOT NULL,
    candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
    source TEXT NOT NULL,  -- 'erc', 'horizon_europe', 'mrc', 'cihr', 'kaken', 'nsfc'
    funder_country TEXT,
    PRIMARY KEY (grant_reference, candidate_uuid)
);
CREATE INDEX IF NOT EXISTS idx_grant_refs_candidate ON grant_refs(candidate_uuid);
CREATE INDEX IF NOT EXISTS idx_grant_refs_source ON grant_refs(source);
CREATE INDEX IF NOT EXISTS idx_grant_refs_country ON grant_refs(funder_country);
