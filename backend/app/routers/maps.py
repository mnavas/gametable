"""Maps: upload, grid config, fog of war."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import storage
from ..database import get_db
from ..deps import get_owned_campaign, get_owned_map
from ..models import Campaign, Map
from ..realtime import hub
from ..schemas import FogUpdate, MapDM, MapUpdate

router = APIRouter(tags=["maps"])


@router.get("/campaigns/{campaign_id}/maps", response_model=list[MapDM])
def list_maps(campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)):
    return db.scalars(
        select(Map).where(Map.campaign_id == campaign.id).order_by(Map.sort_order, Map.created_at)
    ).all()


@router.post("/campaigns/{campaign_id}/maps", response_model=MapDM, status_code=status.HTTP_201_CREATED)
def create_map(
    name: str = Form(...),
    width: int = Form(0),
    height: int = Form(0),
    file: UploadFile = File(...),
    campaign: Campaign = Depends(get_owned_campaign),
    db: Session = Depends(get_db),
):
    image_path = storage.save_public(file, campaign.id)
    m = Map(campaign_id=campaign.id, name=name, image_path=image_path, width=width, height=height)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/maps/{map_id}", response_model=MapDM)
def get_map(m: Map = Depends(get_owned_map)):
    return m


@router.patch("/maps/{map_id}", response_model=MapDM)
def update_map(payload: MapUpdate, m: Map = Depends(get_owned_map), db: Session = Depends(get_db)):
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(m, key, value)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/maps/{map_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_map(m: Map = Depends(get_owned_map), db: Session = Depends(get_db)):
    db.delete(m)
    db.commit()


@router.post("/maps/{map_id}/fog", response_model=MapDM)
async def update_fog(payload: FogUpdate, m: Map = Depends(get_owned_map), db: Session = Depends(get_db)):
    """Reveal/hide a region, or reset. Fog is a list of revealed shapes.

    v1 model: `fog = {"revealed": [shape, ...]}`. 'reveal' appends; 'hide' is
    recorded so the client can subtract it; 'reset' clears. (A richer boolean
    geometry merge can replace this later.)
    """
    fog = dict(m.fog or {})
    revealed = list(fog.get("revealed", []))
    hidden = list(fog.get("hidden", []))

    if payload.op == "reveal" and payload.shape:
        revealed.append(payload.shape)
    elif payload.op == "hide" and payload.shape:
        hidden.append(payload.shape)
    elif payload.op == "reset":
        revealed, hidden = [], []
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid fog op/shape")

    m.fog = {"revealed": revealed, "hidden": hidden}
    db.commit()
    db.refresh(m)

    # Broadcast only if this is the scene players currently see.
    campaign = db.get(Campaign, m.campaign_id)
    if campaign and campaign.active_map_id == m.id:
        # DM gets full fog; players get only the revealed set.
        await hub.broadcast(
            m.campaign_id,
            {"type": "fog", "map_id": str(m.id), "fog": m.fog},
            player_payload={"type": "fog", "map_id": str(m.id), "fog": {"revealed": revealed}},
        )
    return m
