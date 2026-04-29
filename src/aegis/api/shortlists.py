"""Shortlist CRUD endpoints."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from aegis.api.auth import TokenPayload, get_current_customer
from aegis.storage.shortlist_store import ShortlistStore

router = APIRouter(prefix="/v1/shortlists", tags=["shortlists"])


class CreateShortlistRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None


class AddCandidateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_uuid: str


@router.post("")
def create_shortlist(
    body: CreateShortlistRequest,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict:
    store = ShortlistStore()
    shortlist_id = store.create(
        name=body.name, description=body.description, created_by=customer.sub
    )
    store.close()
    return {"id": shortlist_id, "name": body.name}


@router.get("")
def list_shortlists(
    customer: TokenPayload = Depends(get_current_customer),
) -> dict:
    store = ShortlistStore()
    shortlists = store.list_all(created_by=customer.sub)
    store.close()
    return {"shortlists": shortlists}


@router.get("/{shortlist_id}")
def get_shortlist(
    shortlist_id: str,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict:
    store = ShortlistStore()
    shortlist = store.get(shortlist_id)
    members = store.get_members(shortlist_id) if shortlist else []
    store.close()
    if not shortlist:
        raise HTTPException(status_code=404, detail="Shortlist not found")
    return {**shortlist, "members": members}


@router.post("/{shortlist_id}/candidates")
def add_to_shortlist(
    shortlist_id: str,
    body: AddCandidateRequest,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict:
    store = ShortlistStore()
    store.add_candidate(shortlist_id, body.candidate_uuid, added_by=customer.sub)
    store.close()
    return {"status": "added"}


@router.delete("/{shortlist_id}/candidates/{candidate_uuid}")
def remove_from_shortlist(
    shortlist_id: str,
    candidate_uuid: str,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict:
    store = ShortlistStore()
    store.remove_candidate(shortlist_id, candidate_uuid)
    store.close()
    return {"status": "removed"}


@router.delete("/{shortlist_id}")
def delete_shortlist(
    shortlist_id: str,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict:
    store = ShortlistStore()
    store.delete(shortlist_id)
    store.close()
    return {"status": "deleted"}


@router.get("/{shortlist_id}/export")
def export_shortlist(
    shortlist_id: str,
    customer: TokenPayload = Depends(get_current_customer),
) -> StreamingResponse:
    """Export shortlist members as CSV."""
    store = ShortlistStore()
    shortlist = store.get(shortlist_id)
    if not shortlist:
        store.close()
        raise HTTPException(status_code=404, detail="Shortlist not found")
    members = store.get_members(shortlist_id)
    store.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["candidate_uuid", "added_at", "added_by"])
    for m in members:
        writer.writerow([m["candidate_uuid"], m["added_at"], m["added_by"]])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="shortlist_{shortlist_id}.csv"'
        },
    )
