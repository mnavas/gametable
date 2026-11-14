"""DM-side seat management.

Seats are the claimable 'characters' at the table. Players pick one over the
shared link (see player.py); here the DM can see who has claimed what, free a
seat, add one, or remove one. Players never hit these endpoints.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_owned_campaign
from ..models import Campaign, PlayerSeat
from ..schemas import SeatCreate, SeatDM
from .player import broadcast_seats

router = APIRouter(tags=["seats"])


def _owned_seat(seat_id: uuid.UUID, campaign: Campaign, db: Session) -> PlayerSeat:
    seat = db.get(PlayerSeat, seat_id)
    if not seat or seat.campaign_id != campaign.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Seat not found")
    return seat


@router.get("/campaigns/{campaign_id}/seats", response_model=list[SeatDM])
def list_seats(campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)):
    return db.scalars(
        select(PlayerSeat).where(PlayerSeat.campaign_id == campaign.id)
        .order_by(PlayerSeat.sort_order, PlayerSeat.created_at)
    ).all()


@router.post("/campaigns/{campaign_id}/seats", response_model=SeatDM, status_code=status.HTTP_201_CREATED)
async def create_seat(
    payload: SeatCreate, campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)
):
    seat = PlayerSeat(campaign_id=campaign.id, name=payload.name, color=payload.color)
    db.add(seat)
    db.commit()
    db.refresh(seat)
    await broadcast_seats(campaign.id, db)
    return seat


@router.post("/campaigns/{campaign_id}/seats/{seat_id}/reset", response_model=SeatDM)
async def reset_seat(
    seat_id: uuid.UUID, campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)
):
    """Free a claimed seat so a (different) player can take it."""
    seat = _owned_seat(seat_id, campaign, db)
    seat.claimed = False
    seat.claim_token = None
    seat.claimed_by = None
    db.commit()
    db.refresh(seat)
    await broadcast_seats(campaign.id, db)
    return seat


@router.delete("/campaigns/{campaign_id}/seats/{seat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seat(
    seat_id: uuid.UUID, campaign: Campaign = Depends(get_owned_campaign), db: Session = Depends(get_db)
):
    db.delete(_owned_seat(seat_id, campaign, db))
    db.commit()
    await broadcast_seats(campaign.id, db)
