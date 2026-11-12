"""Player-facing API. Share-token scoped; returns PUBLIC content only.

Every response here is built from `*Public` schemas and filters out hidden
tokens, hidden fog, hidden creatures, and private rolls — the share link can be
handed to anyone.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import PlayerContext, get_player_context
from ..models import Creature, DiceRoll, GalleryImage, Map, Token
from ..realtime import hub
from ..schemas import (
    CreaturePublic,
    DiceRollOut,
    GalleryImageOut,
    MapPublic,
    NotePublic,
    PlayerRollRequest,
    PlayerState,
    TokenPublic,
)
from ..security import DiceError, roll_formula
from ..models import Note

router = APIRouter(prefix="/play", tags=["player"])


@router.get("/state", response_model=PlayerState)
def player_state(ctx: PlayerContext = Depends(get_player_context), db: Session = Depends(get_db)):
    campaign = ctx.campaign

    active_map = None
    tokens: list[TokenPublic] = []
    if campaign.active_map_id:
        m = db.get(Map, campaign.active_map_id)
        if m:
            # Players only ever get the revealed fog set.
            fog_revealed = {"revealed": (m.fog or {}).get("revealed", [])}
            active_map = MapPublic.model_validate(m).model_copy(update={"fog": fog_revealed})
            visible = db.scalars(
                select(Token).where(Token.map_id == m.id, Token.hidden_from_players.is_(False)).order_by(Token.z_index)
            ).all()
            tokens = [TokenPublic.model_validate(t) for t in visible]

    active_image = None
    if campaign.active_image_id:
        img = db.get(GalleryImage, campaign.active_image_id)
        if img:
            active_image = GalleryImageOut.model_validate(img)

    return PlayerState(
        campaign_name=campaign.name,
        active_map=active_map,
        tokens=tokens,
        active_image=active_image,
        seat_id=ctx.seat_id,
    )


@router.get("/creatures/{creature_id}", response_model=CreaturePublic)
def player_creature(
    creature_id: uuid.UUID, ctx: PlayerContext = Depends(get_player_context), db: Session = Depends(get_db)
):
    """Click-a-token info. Returns public fields only, and only if visible."""
    creature = db.get(Creature, creature_id)
    if (
        not creature
        or creature.campaign_id != ctx.campaign.id
        or creature.visibility == "hidden"
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return CreaturePublic.model_validate(creature)


@router.get("/notes", response_model=list[NotePublic])
def player_notes(ctx: PlayerContext = Depends(get_player_context), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Note).where(Note.campaign_id == ctx.campaign.id, Note.visibility == "public").order_by(Note.sort_order)
    ).all()
    return [NotePublic.model_validate(n) for n in rows]


@router.get("/dice", response_model=list[DiceRollOut])
def player_dice_log(ctx: PlayerContext = Depends(get_player_context), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(DiceRoll)
        .where(DiceRoll.campaign_id == ctx.campaign.id, DiceRoll.visibility == "public")
        .order_by(DiceRoll.created_at.desc())
        .limit(100)
    ).all()
    return rows


@router.post("/roll", response_model=DiceRollOut)
async def player_roll(
    payload: PlayerRollRequest,
    ctx: PlayerContext = Depends(get_player_context),
    db: Session = Depends(get_db),
):
    try:
        detail = roll_formula(payload.formula)
    except DiceError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    roll = DiceRoll(
        campaign_id=ctx.campaign.id,
        roller_type="player",
        roller_name=payload.player_name,
        seat_id=ctx.seat_id,
        formula=payload.formula,
        detail=detail,
        total=detail["total"],
        visibility=payload.visibility if payload.visibility in ("public", "private") else "public",
    )
    db.add(roll)
    db.commit()
    db.refresh(roll)

    # A player's private roll goes only to the DM (plus the roller's own HTTP response).
    event = {"type": "dice_roll", "roll": DiceRollOut.model_validate(roll).model_dump(mode="json")}
    await hub.broadcast(ctx.campaign.id, event, dm_only=(roll.visibility == "private"))
    return roll
