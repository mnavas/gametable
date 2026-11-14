"""Campaign notes — hidden (DM-only) or public (handout to players)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_owned_campaign
from ..models import Campaign, Note
from ..schemas import NoteCreate, NoteDM, NoteUpdate
from .player import broadcast_notes

router = APIRouter(tags=["notes"])


def _owned_note(note_id: uuid.UUID, campaign: Campaign, db: Session) -> Note:
    note = db.get(Note, note_id)
    if not note or note.campaign_id != campaign.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    return note


@router.get("/campaigns/{campaign_id}/notes", response_model=list[NoteDM])
def list_notes(campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)):
    return db.scalars(
        select(Note).where(Note.campaign_id == campaign.id).order_by(Note.sort_order, Note.created_at)
    ).all()


@router.post("/campaigns/{campaign_id}/notes", response_model=NoteDM, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate, campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)
):
    note = Note(campaign_id=campaign.id, **payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    if note.visibility == "public":
        await broadcast_notes(campaign.id, db)
    return note


@router.patch("/campaigns/{campaign_id}/notes/{note_id}", response_model=NoteDM)
async def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    campaign: Campaign = Depends(get_owned_campaign),
    db: Session = Depends(get_db),
):
    note = _owned_note(note_id, campaign, db)
    was_public = note.visibility == "public"
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, key, value)
    db.commit()
    db.refresh(note)
    # Push to players if this note is (or just stopped being) a public handout.
    if was_public or note.visibility == "public":
        await broadcast_notes(campaign.id, db)
    return note


@router.delete("/campaigns/{campaign_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID, campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)
):
    note = _owned_note(note_id, campaign, db)
    was_public = note.visibility == "public"
    db.delete(note)
    db.commit()
    if was_public:
        await broadcast_notes(campaign.id, db)
