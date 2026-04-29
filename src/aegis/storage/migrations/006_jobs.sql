CREATE TABLE IF NOT EXISTS jobs (
  id               VARCHAR PRIMARY KEY,
  query_text       VARCHAR NOT NULL,
  status           VARCHAR NOT NULL DEFAULT 'in_progress',
  created_at       TIMESTAMP NOT NULL DEFAULT now(),
  completed_at     TIMESTAMP,
  duration_ms      DOUBLE,
  source_count     INTEGER,
  candidate_count  INTEGER,
  created_by       VARCHAR NOT NULL
);
