# Query Latency Budget

End-to-end latency target for a single query scoring pipeline, measured at p95.

| Stage                | Budget (ms) | Description                                      |
|----------------------|-------------|--------------------------------------------------|
| Query expansion      | <= 100      | MeSH term lookup and query vector construction   |
| Topical fit          | <= 200      | Cosine similarity T(c,q) for all candidates      |
| Recency + scoring    | <= 150      | R(c,q) computation and Q(c) percentile lookup    |
| Formatting           | <= 50       | Result serialization and top-k selection          |
| **Total**            | **< 500**   | **p95 end-to-end for 100-candidate cohort**      |
