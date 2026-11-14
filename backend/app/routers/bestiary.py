"""The server-shared bestiary: a cross-DM library of creatures.

A DM contributes a creature by setting its visibility to ``server_shared`` (in
the creature editor). That publishes ONLY the creature's public content — name,
type, public stats, token and display images — to every other DM on the server.
Hidden stats and the hidden image are never part of a shared entry.

Any DM can browse the library and copy an entry into one of their own campaigns.
The copy is independent: image bytes are duplicated into the target campaign's
own media bucket, so it survives the original being edited, unshared, or deleted,
and the new creature starts with empty hidden fields (the copier's to fill in).
"""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import storage
from ..database import get_db
from ..deps import get_current_user
from ..models import Campaign, Creature, User
from ..schemas import BestiaryCopyRequest, BestiaryEntry, CreatureDM

router = APIRouter(tags=["bestiary"])

_SHARED = "server_shared"


@router.get("/bestiary", response_model=list[BestiaryEntry])
def list_bestiary(
    q: str | None = Query(default=None, description="Filter by name"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every creature shared to the server, public fields only."""
    stmt = (
        select(Creature, User.display_name, Campaign.owner_id)
        .join(Campaign, Creature.campaign_id == Campaign.id)
        .join(User, Campaign.owner_id == User.id)
        .where(Creature.visibility == _SHARED)
        .order_by(Creature.name, Creature.created_at)
    )
    if q and q.strip():
        stmt = stmt.where(Creature.name.ilike(f"%{q.strip()}%"))
    rows = db.execute(stmt).all()
    return [
        BestiaryEntry(
            id=cr.id,
            name=cr.name,
            type=cr.type,
            public_stats=cr.public_stats,
            token_image_path=cr.token_image_path,
            display_image_path=cr.display_image_path,
            contributor=display_name,
            mine=(owner_id == user.id),
        )
        for cr, display_name, owner_id in rows
    ]


def _copy_public_media(src_url: str | None, campaign_id: uuid.UUID) -> str | None:
    """Duplicate a public image into the target campaign's bucket. Returns new url."""
    if not src_url:
        return None
    fs = storage.fs_path_for_url(src_url)
    if not fs or not os.path.isfile(fs):
        return None
    with open(fs, "rb") as fh:
        data = fh.read()
    ext = os.path.splitext(fs)[1].lower() or ".png"
    return storage.save_public_bytes(data, ext, campaign_id)


@router.post("/bestiary/{creature_id}/copy", response_model=CreatureDM, status_code=status.HTTP_201_CREATED)
def copy_from_bestiary(
    creature_id: uuid.UUID,
    payload: BestiaryCopyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Copy a shared creature's PUBLIC content into one of the requester's campaigns."""
    src = db.get(Creature, creature_id)
    if not src or src.visibility != _SHARED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not in the shared bestiary")

    campaign = db.get(Campaign, payload.campaign_id)
    if not campaign or campaign.owner_id != user.id:
        # 404 (not 403) so we don't confirm another DM's campaign id.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")

    new = Creature(
        campaign_id=campaign.id,
        name=src.name,
        type=src.type,
        public_stats=src.public_stats,
        hidden_stats="",          # hidden content never crosses DM boundaries
        hidden_image_path=None,
        visibility="campaign_public",
        token_image_path=_copy_public_media(src.token_image_path, campaign.id),
        display_image_path=_copy_public_media(src.display_image_path, campaign.id),
    )
    db.add(new)
    db.commit()
    db.refresh(new)
    return new
