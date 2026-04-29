"""Aegis customer-facing query API server.

Mounts all routers and middleware: JWT auth, rate limiting, audit logging,
query expansion, ranking, result formatting, and staleness detection.
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import asyncio
import hashlib
import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from aegis.api.audit_log import AuditEntry, AuditLog
from aegis.api.auth import (
    TokenPayload,
    get_current_customer,
    require_cohort_access,
)
from aegis.api.formatter import ResultFormatter
from aegis.api.rate_limit import RateLimiterRegistry
from aegis.api.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    ErrorResponse,
    ExpansionInfo,
    QueryRequest,
    QueryResponse,
)
from aegis.api import feedback as feedback_mod
from aegis.api import hitl as hitl_mod
from aegis.api import refit as refit_mod
from aegis.api.notes import router as notes_router
from aegis.api.shortlists import router as shortlists_router
from aegis.api.staleness import StalenessCircuitBreaker
from aegis.api.streaming import close_stream, get_or_create_queue, push_event
from aegis.api.streaming import router as streaming_router

logger = logging.getLogger(__name__)


async def _background_refresh(interval_seconds: float) -> None:
    """Run periodic source refresh in the background."""
    from aegis.ingestion.orchestrator import RefreshOrchestrator

    orchestrator = RefreshOrchestrator()
    while True:
        try:
            summary = await orchestrator.run_full_refresh()
            logger.info(
                "Background refresh: %d/%d sources OK",
                summary.completed,
                summary.total_sources,
            )
        except Exception:
            logger.exception("Background refresh failed")
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: start background refresh on startup."""
    refresh_interval = (
        float(os.environ.get("AEGIS_REFRESH_INTERVAL_HOURS", "6")) * 3600
    )
    refresh_task = asyncio.create_task(_background_refresh(refresh_interval))
    yield
    refresh_task.cancel()
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass


def create_app(
    *,
    audit_log_path: Path | None = None,
    rate_limiter: RateLimiterRegistry | None = None,
    circuit_breaker: StalenessCircuitBreaker | None = None,
    formatter: ResultFormatter | None = None,
) -> FastAPI:
    """Create and configure the Aegis API application."""
    app = FastAPI(
        title="Aegis Expert Discovery API",
        version="1.0.0",
        description="Customer-facing query API for expert discovery and ranking",
        lifespan=lifespan,
    )

    # Mount routers
    app.include_router(shortlists_router)
    app.include_router(notes_router)
    app.include_router(streaming_router)
    app.include_router(feedback_mod.router)
    app.include_router(refit_mod.router)
    app.include_router(hitl_mod.router)

    # Initialize components with defaults
    _audit_log = AuditLog(
        storage_path=audit_log_path or Path("data/aegis/audit_log.jsonl")
    )
    _rate_limiter = rate_limiter or RateLimiterRegistry()
    _circuit_breaker = circuit_breaker or StalenessCircuitBreaker()
    _formatter = formatter or ResultFormatter()

    @app.post(
        "/v1/queries",
        response_model=QueryResponse,
        status_code=status.HTTP_200_OK,
        responses={
            429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
            401: {"model": ErrorResponse, "description": "Authentication failed"},
            403: {"model": ErrorResponse, "description": "Access denied"},
        },
    )
    async def submit_query(
        body: QueryRequest,
        customer: TokenPayload = Depends(get_current_customer),
    ) -> QueryResponse | JSONResponse:
        """Submit a query for expert ranking."""
        start_time = time.monotonic()

        # 1. Cohort access check
        require_cohort_access(customer, body.cohort_filter)

        # 2. Rate limit check
        query_hash = hashlib.sha256(
            body.task_description.encode()
        ).hexdigest()[:16]
        rl_result = _rate_limiter.check(
            customer_id=customer.sub,
            rate=float(customer.rate_limit_qps),
            capacity=float(customer.rate_limit_qps) * 2,
            query_hash=query_hash,
        )
        if not rl_result.allowed:
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error="rate_limit_exceeded",
                    detail="Too many requests",
                    retry_after=int(rl_result.retry_after_seconds or 1),
                ).model_dump(),
                headers={
                    "Retry-After": str(int(rl_result.retry_after_seconds or 1))
                },
            )

        # 3. Check staleness
        staleness_warnings = _circuit_breaker.check_all()

        # 4. Execute the real pipeline
        from aegis.pipeline.orchestrator import QueryPipeline, SourceProgress

        pipeline = QueryPipeline()

        # Pre-generate query_id for SSE streaming
        import uuid as uuid_mod

        query_id = uuid_mod.uuid4().hex
        get_or_create_queue(query_id)

        def _progress_callback(progress: SourceProgress) -> None:
            push_event(query_id, "source_progress", progress.model_dump())

        try:
            pipeline_result = await pipeline.execute(
                task_description=body.task_description,
                mesh_override=body.mesh_override,
                k=body.k,
                progress_callback=_progress_callback,
            )
        except Exception:
            close_stream(query_id)
            raise

        # 5. Build affiliations dict from DuckDB candidates
        from aegis.storage.candidate_store import CandidateStore

        _store = CandidateStore()
        all_candidates = _store.list_by_cohort(body.cohort_filter)
        _store.close()

        affiliations = {
            c.uuid: (
                c.affiliations[0].canonical_name if c.affiliations else "Unknown",
                c.affiliations[0].country if c.affiliations else None,
            )
            for c in all_candidates
        }

        # 6. Build F-scores dict for formatter
        f_scores: dict[str, dict[str, float]] = {
            "f1": pipeline_result.f1_scores,
            "f2": pipeline_result.f2_scores,
            "f3": pipeline_result.f3_scores,
            "f4": pipeline_result.f4_scores,
            "f5": pipeline_result.f5_scores,
            "f6": pipeline_result.f6_scores,
        }
        if pipeline_result.f7_scores is not None:
            f_scores["f7"] = pipeline_result.f7_scores

        # 7. Format response
        response = _formatter.format(
            ranked=pipeline_result.ranked_list,
            expansion_info=pipeline_result.expansion_info,
            variance_bands=pipeline_result.variance_bands,
            affiliations=affiliations,
            staleness_warnings=staleness_warnings,
            f_scores=f_scores,
        )

        # Override query_id to match the one we pre-generated for SSE
        response = response.model_copy(update={"query_id": query_id})

        # 8. Audit log
        elapsed_ms = (time.monotonic() - start_time) * 1000
        _audit_log.append(
            entry=AuditEntry(
                request_id=response.query_id,
                customer_id=customer.sub,
                customer_name=customer.customer_name,
                timestamp=datetime.now(UTC),
                endpoint="POST /v1/queries",
                query_text=body.task_description,
                expanded_mesh_terms=pipeline_result.expansion_info.expanded_mesh_terms,
                response_candidate_uuids=[
                    c.candidate_uuid for c in response.candidates
                ],
                weight_version=pipeline_result.ranked_list.weight_version,
                integrity_rule_version=_formatter._integrity_rule_version,
                latency_ms=round(elapsed_ms, 2),
                status_code=200,
                cohort_filter=body.cohort_filter,
            )
        )

        # 9. Store query in QueryStore (DuckDB)
        from aegis.storage.query_store import QueryStore

        try:
            query_store = QueryStore()
            query_store.save(
                query_id=response.query_id,
                task_description=body.task_description,
                query_type=pipeline_result.query_type,
                weight_vector_name=pipeline_result.weight_vector_name,
                mesh_terms=pipeline_result.expansion_info.expanded_mesh_terms,
                k=body.k,
                result_count=len(response.candidates),
                candidate_uuids=[c.candidate_uuid for c in response.candidates],
                candidate_scores=[c.model_dump() for c in response.candidates],
                pipeline_duration_ms=pipeline_result.pipeline_duration_ms,
                created_by=customer.sub,
            )
            query_store.close()
        except Exception:
            logger.exception("Failed to store query in QueryStore")

        # 10. Push complete SSE event and close stream
        push_event(query_id, "complete", {
            "query_id": response.query_id,
            "result_count": len(response.candidates),
            "pipeline_duration_ms": pipeline_result.pipeline_duration_ms,
        })
        close_stream(query_id)

        return response

    @app.post("/v1/queries/classify")
    def classify_query(body: ClassifyRequest) -> ClassifyResponse:
        """Classify a query and return detected type + weight vector."""
        from aegis.query.classifier import QueryClassifier

        classifier = QueryClassifier()
        result = classifier.classify(body.task_description)
        return ClassifyResponse(
            query_type=result.query_type,
            confidence=result.confidence,
            keyword_matches=result.keyword_matches,
            weights=result.weight_vector.weights,
            exponents=result.weight_vector.exponents,
        )

    @app.get("/v1/queries")
    def list_queries(
        page: int = 1,
        per_page: int = 20,
        customer: TokenPayload = Depends(get_current_customer),
    ) -> dict:
        """List past queries, newest first."""
        from aegis.storage.query_store import QueryStore

        try:
            query_store = QueryStore()
            queries, total = query_store.list_all(
                page=page,
                per_page=per_page,
                created_by=customer.sub,
            )
            query_store.close()
        except Exception:
            logger.exception("Failed to list queries from QueryStore")
            queries, total = [], 0

        return {
            "queries": [
                {
                    "id": q["id"],
                    "task_description": q["task_description"],
                    "query_type": q.get("query_type"),
                    "k": q["k"],
                    "result_count": q["result_count"],
                    "created_at": q["created_at"],
                    "custom_name": q.get("custom_name"),
                }
                for q in queries
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    @app.get("/v1/queries/{query_id}")
    def get_query(
        query_id: str,
        customer: TokenPayload = Depends(get_current_customer),
    ) -> dict:
        """Get a specific query result by ID."""
        from aegis.storage.query_store import QueryStore

        try:
            query_store = QueryStore()
            query = query_store.get(query_id)
            query_store.close()
        except Exception:
            logger.exception("Failed to get query from QueryStore")
            query = None

        if not query:
            raise HTTPException(status_code=404, detail="Query not found")

        # Shape response to match the BackendQueryResponse interface expected by the frontend proxy.
        # candidate_scores stores the serialized CandidateResult list saved at query time.
        return {
            "id": query["id"],
            "task_description": query["task_description"],
            "population": None,
            "k": query["k"],
            "candidates": query.get("candidate_scores") or [],
            "created_at": str(query["created_at"]),
            "mesh_override": query.get("mesh_terms"),
            "cutoff_strategy": None,
            "result_count": query["result_count"],
            "query_type": query.get("query_type"),
            "weight_vector_name": query.get("weight_vector_name"),
        }

    @app.get("/v1/candidates/{uuid}/evidence")
    def get_candidate_evidence(
        uuid: str,
        customer: TokenPayload = Depends(get_current_customer),
    ) -> dict:
        """Get evidence trail for a candidate."""
        from aegis.storage.candidate_store import CandidateStore

        store = CandidateStore()
        candidate = store.get_by_uuid(uuid)

        if candidate is None:
            store.close()
            raise HTTPException(status_code=404, detail="Candidate not found")

        name = candidate.name_variants[0] if candidate.name_variants else uuid
        items = []

        # Narrative evidence strings (tagged with the source they mention)
        for line in candidate.evidence_trail:
            src = "aegis"
            if "pubmed" in line.lower() or "publication" in line.lower():
                src = "pubmed"
            elif any(k in line.lower() for k in ["grant", "nih", "erc", "mrc", "cihr", "kaken"]):
                src = "reporter"
            elif "trial" in line.lower() or "nct" in line.lower():
                src = "clinicaltrials"
            items.append({"type": "narrative", "source": src, "description": line})

        # PubMed artifacts
        for pmid in candidate.artifact_refs.pmids[:10]:
            items.append({
                "type": "pmid",
                "source": "pubmed",
                "description": f"PubMed publication {pmid}",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}",
            })

        # iCite RCR scores (stored as artifact_refs with type pmid_rcr)
        icite_rows = store._conn.execute(
            "SELECT artifact_id FROM artifact_refs WHERE candidate_uuid = ? AND artifact_type = 'pmid_rcr'",
            [uuid],
        ).fetchall()
        for (artifact_id,) in icite_rows:
            # artifact_id format: "12345678:rcr=2.340"
            if ":rcr=" in artifact_id:
                pmid_part, rcr_part = artifact_id.split(":rcr=", 1)
                try:
                    rcr_val = float(rcr_part)
                    percentile = "above" if rcr_val > 1.0 else "below"
                    items.append({
                        "type": "rcr_score",
                        "source": "icite",
                        "description": (
                            f"PMID {pmid_part}: RCR {rcr_val:.2f} "
                            f"({percentile} field average of 1.0)"
                        ),
                        "url": f"https://icite.od.nih.gov/analysis?search_id={pmid_part}",
                        "score_contribution": round(min(rcr_val / 5.0, 1.0), 3),
                    })
                except ValueError:
                    pass

        # Grant artifacts — infer source from grant ID prefix
        _grant_source_url = {
            "R": ("reporter", "https://reporter.nih.gov/project-details/{id}"),
            "P": ("reporter", "https://reporter.nih.gov/project-details/{id}"),
            "U": ("reporter", "https://reporter.nih.gov/project-details/{id}"),
            "K": ("reporter", "https://reporter.nih.gov/project-details/{id}"),
            "ERC": ("erc", "https://cordis.europa.eu/project/id/{id}"),
            "MRC": ("mrc", "https://gtr.ukri.org/projects?ref={id}"),
            "CIHR": ("cihr", "https://webapps.cihr-irsc.gc.ca/decisions/p/search.html"),
            "KAKENHI": ("kaken", "https://kaken.nii.ac.jp/grant/{id}"),
        }

        for grant_id in candidate.artifact_refs.grant_ids:
            src = "reporter"
            url_template = "https://reporter.nih.gov/project-details/{id}"
            for prefix, (gsrc, gtmpl) in _grant_source_url.items():
                if grant_id.upper().startswith(prefix):
                    src = gsrc
                    url_template = gtmpl
                    break
            items.append({
                "type": "grant",
                "source": src,
                "description": f"Grant {grant_id}",
                "url": url_template.replace("{id}", grant_id),
            })

        # Clinical trial artifacts
        for nct_id in candidate.artifact_refs.nct_ids:
            items.append({
                "type": "clinical_trial",
                "source": "clinicaltrials",
                "description": f"ClinicalTrials.gov study {nct_id}",
                "url": f"https://clinicaltrials.gov/study/{nct_id}",
            })

        store.close()
        return {
            "candidate_uuid": uuid,
            "candidate_name": name,
            "evidence_items": items,
        }

    @app.get("/v1/health")
    def health_check() -> dict:
        """Health check with component status."""
        from aegis.storage.candidate_store import CandidateStore

        try:
            store = CandidateStore()
            count = store.count()
            store.close()
            db_status = "healthy"
        except Exception:
            count = 0
            db_status = "unhealthy"
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "version": "5.0.0",
            "database": db_status,
            "candidate_count": count,
        }

    return app


# Module-level app instance for uvicorn: `uvicorn aegis.api.server:app`
app = create_app()
