"""Creature/NPC/player library. DM sees everything; players get CreaturePublic."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import storage
from ..database import get_db
from ..deps import get_owned_campaign, get_owned_creature
from ..models import Campaign, Creature
from ..schemas import CreatureCreate, CreatureDM, CreatureUpdate

router = APIRouter(tags=["creatures"])


@router.get("/campaigns/{campaign_id}/creatures", response_model=list[CreatureDM])
def list_creatures(campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)):
    return db.scalars(
        select(Creature).where(Creature.campaign_id == campaign.id).order_by(Creature.name)
    ).all()


@router.post("/campaigns/{campaign_id}/creatures", response_model=CreatureDM, status_code=status.HTTP_201_CREATED)
def create_creature(
    payload: CreatureCreate,
    campaign: Campaign = Depends(get_owned_campaign),
    db: Session = Depends(get_db),
):
    creature = Creature(campaign_id=campaign.id, **payload.model_dump())
    db.add(creature)
    db.commit()
    db.refresh(creature)
    return creature


@router.get("/creatures/{creature_id}", response_model=CreatureDM)
def get_creature(creature: Creature = Depends(get_owned_creature)):
    return creature


@router.patch("/creatures/{creature_id}", response_model=CreatureDM)
def update_creature(
    payload: CreatureUpdate, creature: Creature = Depends(get_owned_creature), db: Session = Depends(get_db)
):
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(creature, key, value)
    db.commit()
    db.refresh(creature)
    return creature


@router.delete("/creatures/{creature_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_creature(creature: Creature = Depends(get_owned_creature), db: Session = Depends(get_db)):
    db.delete(creature)
    db.commit()


# --- Images -----------------------------------------------------------------

@router.put("/creatures/{creature_id}/token-image", response_model=CreatureDM)
def set_token_image(
    file: UploadFile = File(...), creature: Creature = Depends(get_owned_creature), db: Session = Depends(get_db)
):
    creature.token_image_path = storage.save_public(file, creature.campaign_id)
    db.commit()
    db.refresh(creature)
    return creature


@router.put("/creatures/{creature_id}/display-image", response_model=CreatureDM)
def set_display_image(
    file: UploadFile = File(...), creature: Creature = Depends(get_owned_creature), db: Session = Depends(get_db)
):
    # Public — shown to players on click.
    creature.display_image_path = storage.save_public(file, creature.campaign_id)
    db.commit()
    db.refresh(creature)
    return creature


@router.put("/creatures/{creature_id}/hidden-image", response_model=CreatureDM)
def set_hidden_image(
    file: UploadFile = File(...), creature: Creature = Depends(get_owned_creature), db: Session = Depends(get_db)
):
    # DM-only — stored in the protected bucket, never a public URL.
    creature.hidden_image_path = storage.save_protected(file, creature.campaign_id)
    db.commit()
    db.refresh(creature)
    return creature
