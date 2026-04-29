"""Jobs API endpoints for async pipeline job management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from aegis.api.auth import TokenPayload, get_current_customer
from aegis.storage.job_store import JobStore

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    page: int = 1,
    per_page: int = 20,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict[str, Any]:
    store = JobStore()
    jobs, total = store.list_all(created_by=customer.sub, page=page, per_page=per_page)
    store.close()
    return {"jobs": jobs, "total": total, "page": page, "per_page": per_page}


@router.get("/{job_id}")
def get_job(
    job_id: str,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict[str, Any]:
    store = JobStore()
    job = store.get(job_id)
    store.close()
    if not job or job["created_by"] != customer.sub:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: str,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict[str, str]:
    store = JobStore()
    job = store.get(job_id)
    if not job or job["created_by"] != customer.sub:
        store.close()
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "in_progress":
        store.close()
        raise HTTPException(
            status_code=409,
            detail=f"Job is already {job['status']}",
        )
    # Lazy import to avoid circular dependency
    from aegis.api import server as server_mod

    task = server_mod._task_registry.get(job_id)  # type: ignore[attr-defined]
    if task is not None:
        task.cancel()
    store.update(job_id, status="cancelled")
    store.close()
    return {"status": "cancelled"}
