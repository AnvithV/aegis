-- Candidates table: stores full candidate records as JSON with denormalized lookup columns
CREATE TABLE IF NOT EXISTS candidates (
    uuid TEXT PRIMARY KEY,
    data JSON NOT NULL,
    linkage_confidence DOUBLE,
    created_at TIMESTAMP DEFAULT current_timestamp,
    updated_at TIMESTAMP DEFAULT current_timestamp
);

-- Strong keys lookup table for fast identity resolution
CREATE TABLE IF NOT EXISTS strong_keys (
    key_type TEXT NOT NULL,
    key_value TEXT NOT NULL,
    candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
    PRIMARY KEY (key_type, key_value)
);

-- Artifact references for cross-source joins
CREATE TABLE IF NOT EXISTS artifact_refs (
    artifact_type TEXT NOT NULL,  -- 'pmid', 'nct_id', 'grant_id'
    artifact_id TEXT NOT NULL,
    candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
    PRIMARY KEY (artifact_type, artifact_id, candidate_uuid)
);

-- Sequence for affiliation_history IDs
CREATE SEQUENCE IF NOT EXISTS affiliation_history_id_seq;

-- Affiliation history for time-based queries
CREATE TABLE IF NOT EXISTS affiliation_history (
    id INTEGER PRIMARY KEY DEFAULT nextval('affiliation_history_id_seq'),
    candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
    ror_id TEXT,
    canonical_name TEXT NOT NULL,
    raw_string TEXT NOT NULL,
    country TEXT,
    confidence DOUBLE,
    start_date DATE,
    end_date DATE
);
