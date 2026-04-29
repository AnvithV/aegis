CREATE TABLE IF NOT EXISTS shortlists (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    created_by VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS shortlist_members (
    shortlist_id VARCHAR NOT NULL,
    candidate_uuid VARCHAR NOT NULL,
    added_at TIMESTAMP NOT NULL,
    added_by VARCHAR NOT NULL,
    PRIMARY KEY (shortlist_id, candidate_uuid)
);

CREATE TABLE IF NOT EXISTS candidate_notes (
    id VARCHAR PRIMARY KEY,
    candidate_uuid VARCHAR NOT NULL,
    author VARCHAR NOT NULL,
    content VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS query_history (
    id VARCHAR PRIMARY KEY,
    task_description VARCHAR NOT NULL,
    query_type VARCHAR,
    weight_vector_name VARCHAR,
    mesh_terms VARCHAR,
    k INTEGER NOT NULL,
    result_count INTEGER NOT NULL,
    candidate_uuids VARCHAR,
    candidate_scores VARCHAR,
    pipeline_duration_ms DOUBLE,
    created_at TIMESTAMP NOT NULL,
    created_by VARCHAR,
    custom_name VARCHAR
);
