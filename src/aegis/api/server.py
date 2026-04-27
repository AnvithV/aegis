"""Aegis customer-facing query API server.

Mounts all routers and middleware: JWT auth, rate limiting, audit logging,
query expansion, ranking, result formatting, and staleness detection.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, status
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
    ErrorResponse,
    ExpansionInfo,
    QueryRequest,
    QueryResponse,
)
from aegis.api.staleness import StalenessCircuitBreaker

logger = logging.getLogger(__name__)


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
    )

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
    def submit_query(
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

        # 4. Query expansion (stub: in production, wire LlmQueryExpander here)
        if body.mesh_override:
            expansion_info = ExpansionInfo(
                original_query=body.task_description,
                expanded_mesh_terms=body.mesh_override,
                expansion_method="override",
                low_confidence=False,
                cached=False,
            )
        else:
            # Placeholder: in production, call LlmQueryExpander.expand()
            expansion_info = ExpansionInfo(
                original_query=body.task_description,
                expanded_mesh_terms=[],
                expansion_method="pending_integration",
                low_confidence=True,
                cached=False,
            )

        # 5. Ranking (stub: in production, wire Ranker here)
        from aegis.scoring.result_format import RankedList

        ranked = RankedList(
            query_mesh_terms=expansion_info.expanded_mesh_terms,
            cohort_size=0,
            result_count=0,
            candidates=[],
            excluded_count=0,
            weight_version=1,
            exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
            metadata={},
        )

        # 6. Format response
        response = _formatter.format(
            ranked=ranked,
            expansion_info=expansion_info,
            staleness_warnings=staleness_warnings,
        )

        # 7. Audit log
        elapsed_ms = (time.monotonic() - start_time) * 1000
        _audit_log.append(
            entry=AuditEntry(
                request_id=response.query_id,
                customer_id=customer.sub,
                customer_name=customer.customer_name,
                timestamp=datetime.now(UTC),
                endpoint="POST /v1/queries",
                query_text=body.task_description,
                expanded_mesh_terms=expansion_info.expanded_mesh_terms,
                response_candidate_uuids=[
                    c.candidate_uuid for c in response.candidates
                ],
                weight_version=ranked.weight_version,
                integrity_rule_version=_formatter._integrity_rule_version,
                latency_ms=round(elapsed_ms, 2),
                status_code=200,
                cohort_filter=body.cohort_filter,
            )
        )

        return response

    @app.get("/v1/health")
    def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "version": "1.0.0"}

    return app
