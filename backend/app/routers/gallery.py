"""Campaign gallery + push-a-handout-to-players."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import storage
from ..database import get_db
from ..deps import get_owned_campaign
from ..models import Campaign, GalleryImage
from ..realtime import hub
from ..schemas import GalleryImageOut

router = APIRouter(tags=["gallery"])


def _owned_image(image_id: uuid.UUID, campaign: Campaign, db: Session) -> GalleryImage:
    img = db.get(GalleryImage, image_id)
    if not img or img.campaign_id != campaign.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    return img


@router.get("/campaigns/{campaign_id}/gallery", response_model=list[GalleryImageOut])
def list_gallery(campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)):
    return db.scalars(
        select(GalleryImage).where(GalleryImage.campaign_id == campaign.id).order_by(GalleryImage.created_at.desc())
    ).all()


@router.post("/campaigns/{campaign_id}/gallery", response_model=GalleryImageOut, status_code=status.HTTP_201_CREATED)
def upload_gallery_image(
    name: str = Form(...),
    file: UploadFile = File(...),
    campaign: Campaign = Depends(get_owned_campaign),
    db: Session = Depends(get_db),
):
    img = GalleryImage(campaign_id=campaign.id, name=name, image_path=storage.save_public(file, campaign.id))
    db.add(img)
    db.commit()
    db.refresh(img)
    return img


@router.post("/campaigns/{campaign_id}/gallery/{image_id}/share", response_model=GalleryImageOut)
async def share_image(
    image_id: uuid.UUID, campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)
):
    """Push this image to players (they can switch to it / be shown it)."""
    img = _owned_image(image_id, campaign, db)
    # Only one shared image at a time.
    for other in campaign.gallery:
        other.is_shared = other.id == img.id
    campaign.active_image_id = img.id
    db.commit()
    db.refresh(img)
    await hub.broadcast(campaign.id, {"type": "active_image", "image_id": str(img.id), "image_path": img.image_path})
    return img


@router.post("/campaigns/{campaign_id}/gallery/{image_id}/unshare", status_code=status.HTTP_204_NO_CONTENT)
async def unshare_image(
    image_id: uuid.UUID, campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)
):
    img = _owned_image(image_id, campaign, db)
    img.is_shared = False
    if campaign.active_image_id == img.id:
        campaign.active_image_id = None
    db.commit()
    await hub.broadcast(campaign.id, {"type": "active_image", "image_id": None})


@router.delete("/campaigns/{campaign_id}/gallery/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gallery_image(
    image_id: uuid.UUID, campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)
):
    img = _owned_image(image_id, campaign, db)
    if campaign.active_image_id == img.id:
        campaign.active_image_id = None
    db.delete(img)
    db.commit()
