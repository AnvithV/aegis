"""Candidate notes CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from aegis.api.auth import TokenPayload, get_current_customer
from aegis.storage.notes_store import NotesStore

router = APIRouter(prefix="/v1/candidates", tags=["notes"])


class CreateNoteRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str


class UpdateNoteRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str


@router.post("/{candidate_uuid}/notes")
def create_note(
    candidate_uuid: str,
    body: CreateNoteRequest,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict:
    store = NotesStore()
    note_id = store.create(
        candidate_uuid=candidate_uuid, author=customer.sub, content=body.content
    )
    store.close()
    return {"id": note_id}


@router.get("/{candidate_uuid}/notes")
def list_notes(
    candidate_uuid: str,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict:
    store = NotesStore()
    notes = store.get_for_candidate(candidate_uuid)
    store.close()
    return {"notes": notes}


@router.put("/{candidate_uuid}/notes/{note_id}")
def update_note(
    candidate_uuid: str,
    note_id: str,
    body: UpdateNoteRequest,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict:
    store = NotesStore()
    store.update(note_id, body.content)
    store.close()
    return {"status": "updated"}


@router.delete("/{candidate_uuid}/notes/{note_id}")
def delete_note(
    candidate_uuid: str,
    note_id: str,
    customer: TokenPayload = Depends(get_current_customer),
) -> dict:
    store = NotesStore()
    store.delete(note_id)
    store.close()
    return {"status": "deleted"}
