"""Campaign CRUD, share links, and dice — the DM-owned surface."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_owned_campaign
from ..models import Campaign, DiceRoll, ShareLink
from ..realtime import hub
from ..schemas import (
    CampaignCreate,
    CampaignOut,
    CampaignUpdate,
    DiceRollOut,
    RollRequest,
    ShareLinkCreate,
    ShareLinkOut,
)
from ..security import generate_share_token, hash_password, roll_formula, DiceError
from fastapi import HTTPException

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.scalars(
        select(Campaign).where(Campaign.owner_id == user.id).order_by(Campaign.created_at.desc())
    ).all()
    return rows


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    campaign = Campaign(owner_id=user.id, name=payload.name, description=payload.description)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign: Campaign = Depends(get_owned_campaign)):
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    payload: CampaignUpdate,
    campaign: Campaign = Depends(get_owned_campaign),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(campaign, key, value)
    db.commit()
    db.refresh(campaign)

    # Switching the active map or pushed image is a live event for players.
    if "active_map_id" in data:
        await hub.broadcast(campaign.id, {"type": "active_map", "map_id": str(campaign.active_map_id) if campaign.active_map_id else None})
    if "active_image_id" in data:
        await hub.broadcast(campaign.id, {"type": "active_image", "image_id": str(campaign.active_image_id) if campaign.active_image_id else None})
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)):
    db.delete(campaign)
    db.commit()


# --- Share links ------------------------------------------------------------

@router.get("/{campaign_id}/share-links", response_model=list[ShareLinkOut])
def list_share_links(campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)):
    return db.scalars(select(ShareLink).where(ShareLink.campaign_id == campaign.id)).all()


@router.post("/{campaign_id}/share-links", response_model=ShareLinkOut, status_code=status.HTTP_201_CREATED)
def create_share_link(
    payload: ShareLinkCreate,
    campaign: Campaign = Depends(get_owned_campaign),
    db: Session = Depends(get_db),
):
    link = ShareLink(
        campaign_id=campaign.id,
        token=generate_share_token(),
        label=payload.label,
        kind=payload.kind,
        seat_id=payload.seat_id,
        password_hash=hash_password(payload.password) if payload.password else None,
        expires_at=payload.expires_at,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.delete("/{campaign_id}/share-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share_link(
    link_id: uuid.UUID,
    campaign: Campaign = Depends(get_owned_campaign),
    db: Session = Depends(get_db),
):
    link = db.get(ShareLink, link_id)
    if link and link.campaign_id == campaign.id:
        link.revoked = True
        db.commit()


# --- Dice (DM) --------------------------------------------------------------

@router.get("/{campaign_id}/dice", response_model=list[DiceRollOut])
def dm_dice_log(campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)):
    return db.scalars(
        select(DiceRoll).where(DiceRoll.campaign_id == campaign.id).order_by(DiceRoll.created_at.desc()).limit(100)
    ).all()


@router.post("/{campaign_id}/roll", response_model=DiceRollOut)
async def dm_roll(
    payload: RollRequest,
    campaign: Campaign = Depends(get_owned_campaign),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        detail = roll_formula(payload.formula)
    except DiceError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    roll = DiceRoll(
        campaign_id=campaign.id,
        roller_type="dm",
        roller_name=user.display_name,
        formula=payload.formula,
        detail=detail,
        total=detail["total"],
        visibility=payload.visibility if payload.visibility in ("public", "private") else "public",
    )
    db.add(roll)
    db.commit()
    db.refresh(roll)

    event = {"type": "dice_roll", "roll": DiceRollOut.model_validate(roll).model_dump(mode="json")}
    # A private (silent) DM roll goes only to the DM connections.
    await hub.broadcast(campaign.id, event, dm_only=(roll.visibility == "private"))
    return roll
