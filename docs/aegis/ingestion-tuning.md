# Ingestion Tuning Notes

Batch-size and rate-limit configuration for each public data source.

## PubMed (E-utilities)

| Parameter       | Value | Rationale                                                                 |
|-----------------|-------|---------------------------------------------------------------------------|
| `batch_size`    | 200   | 200 is the E-utilities maximum for `efetch`; no benefit to going lower.   |
| Rate limit      | 3 req/s (without API key), 10 req/s (with API key) | NCBI enforced.       |
| Throughput est. | ~2,000 records/min with API key at batch_size=200                         |

The `search_and_fetch` method accepts `batch_size` as a parameter, defaulting to 200.
PubMed search uses `esearch` to get PMIDs, then `efetch` in batches of `batch_size`.

## NIH RePORTER (v2 API)

| Parameter       | Value | Rationale                                                                 |
|-----------------|-------|---------------------------------------------------------------------------|
| `page_size`     | 500   | 500 is the API maximum; empirically stable at this size.                  |
| Rate limit      | No published hard limit; ~60 req/min observed safe threshold.             |
| Throughput est. | ~30,000 records/min at page_size=500                                      |

The `fetch_grants_by_topic` and `fetch_grants_by_pi` methods accept `page_size` as a parameter.
RePORTER API uses POST with JSON body; pagination via `offset` + `limit`.

## ClinicalTrials.gov (v2 API)

| Parameter       | Value | Rationale                                                                 |
|-----------------|-------|---------------------------------------------------------------------------|
| `page_size`     | 100   | 100 balances throughput vs response time; 1000 causes occasional timeouts on complex queries. |
| Rate limit      | No published hard limit; ~30 req/min observed safe threshold.             |
| Throughput est. | ~3,000 records/min at page_size=100                                       |

The `fetch_studies_by_condition` method accepts `page_size` as a parameter, defaulting to 100.
CT.gov v2 uses GET with query params; pagination via `pageToken`.

## Retry Policy

All three clients share a centralized `RetryPolicy` that provides:

- Exponential back-off on HTTP 429 (rate limited) and 503 (service unavailable)
- Maximum 3 retries per request
- Per-API retry budget of 100 retries per 5-minute window
- Jitter of +/-10% on back-off delays

## Configuration

Batch sizes are configurable per-call via method parameters. To override defaults:

```python
# PubMed: smaller batches for constrained environments
async for record in pubmed.search_and_fetch("cancer", batch_size=50):
    ...

# RePORTER: use max page size (default)
async for grant in reporter.fetch_grants_by_topic(["Cancer"], page_size=500):
    ...

# CT.gov: increase page size for simple queries
async for study in ctgov.fetch_studies_by_condition(["Diabetes"], page_size=500):
    ...
```
