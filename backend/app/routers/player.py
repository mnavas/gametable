"""Player-facing API. Share-token scoped; returns PUBLIC content only.

Every response here is built from `*Public` schemas and filters out hidden
tokens, hidden fog, hidden creatures, and private rolls — the share link can be
handed to anyone.
"""
from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import PlayerContext, get_player_context
from ..models import Creature, DiceRoll, GalleryImage, Map, PlayerSeat, Token
from ..realtime import hub
from ..schemas import (
    CreaturePublic,
    DiceRollOut,
    GalleryImageOut,
    MapPublic,
    NotePublic,
    PlayerRollRequest,
    PlayerState,
    SeatClaimRequest,
    SeatClaimResponse,
    SeatPublic,
    SeatReleaseRequest,
    TokenPublic,
)
from ..security import DiceError, roll_formula
from ..models import Note

router = APIRouter(prefix="/play", tags=["player"])


# --- Seats: pick a character over the shared link ---------------------------

def _seat_token_image(db: Session, campaign_id: uuid.UUID, seat_id: uuid.UUID) -> str | None:
    """The token art of the character a seat controls, for the picker thumbnail."""
    tok = db.scalar(
        select(Token).join(Map, Token.map_id == Map.id).where(
            Map.campaign_id == campaign_id, Token.owner_seat_id == seat_id
        )
    )
    if tok and tok.creature_id:
        cr = db.get(Creature, tok.creature_id)
        if cr:
            return cr.token_image_path
    return None


def _seats_public(db: Session, campaign_id: uuid.UUID) -> list[SeatPublic]:
    seats = db.scalars(
        select(PlayerSeat).where(PlayerSeat.campaign_id == campaign_id)
        .order_by(PlayerSeat.sort_order, PlayerSeat.created_at)
    ).all()
    return [
        SeatPublic(
            id=s.id, name=s.name, color=s.color, claimed=s.claimed, claimed_by=s.claimed_by,
            token_image_path=_seat_token_image(db, campaign_id, s.id),
        )
        for s in seats
    ]


async def broadcast_notes(campaign_id: uuid.UUID, db: Session) -> None:
    """Push the current public notes to players, so handouts appear/vanish live."""
    rows = db.scalars(
        select(Note).where(Note.campaign_id == campaign_id, Note.visibility == "public")
        .order_by(Note.sort_order)
    ).all()
    payload = {
        "type": "notes",
        "notes": [NotePublic.model_validate(n).model_dump(mode="json") for n in rows],
    }
    # Players only — the DM already has the full list in their editor.
    await hub.broadcast(campaign_id, None, player_payload=payload)


async def broadcast_seats(campaign_id: uuid.UUID, db: Session) -> None:
    """Tell every connected client the current claim state (so pickers update live)."""
    seats = db.scalars(
        select(PlayerSeat).where(PlayerSeat.campaign_id == campaign_id)
        .order_by(PlayerSeat.sort_order, PlayerSeat.created_at)
    ).all()
    payload = {
        "type": "seats",
        "seats": [
            {"id": str(s.id), "name": s.name, "color": s.color, "claimed": s.claimed, "claimed_by": s.claimed_by}
            for s in seats
        ],
    }
    await hub.broadcast(campaign_id, payload)


def _resolve_seat(db: Session, campaign_id: uuid.UUID, claim_token: str | None) -> uuid.UUID | None:
    if not claim_token:
        return None
    s = db.scalar(
        select(PlayerSeat).where(
            PlayerSeat.campaign_id == campaign_id, PlayerSeat.claim_token == claim_token
        )
    )
    return s.id if s else None


@router.get("/seats", response_model=list[SeatPublic])
def list_seats(ctx: PlayerContext = Depends(get_player_context), db: Session = Depends(get_db)):
    return _seats_public(db, ctx.campaign.id)


@router.post("/seats/{seat_id}/claim", response_model=SeatClaimResponse)
async def claim_seat(
    seat_id: uuid.UUID,
    payload: SeatClaimRequest,
    ctx: PlayerContext = Depends(get_player_context),
    db: Session = Depends(get_db),
):
    seat = db.get(PlayerSeat, seat_id)
    if not seat or seat.campaign_id != ctx.campaign.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Character not found")
    claim = secrets.token_urlsafe(24)
    # Atomic claim: only succeeds if the seat is still free (guards a race between
    # two players tapping the same character at once).
    res = db.execute(
        update(PlayerSeat)
        .where(PlayerSeat.id == seat_id, PlayerSeat.claimed.is_(False))
        .values(claimed=True, claim_token=claim, claimed_by=payload.player_name[:120])
    )
    if res.rowcount == 0:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "That character is already taken")
    db.commit()
    await broadcast_seats(ctx.campaign.id, db)
    return SeatClaimResponse(seat_id=seat.id, claim_token=claim, name=seat.name, color=seat.color)


@router.post("/seats/release")
async def release_seat(
    payload: SeatReleaseRequest,
    ctx: PlayerContext = Depends(get_player_context),
    db: Session = Depends(get_db),
):
    seat = db.scalar(
        select(PlayerSeat).where(
            PlayerSeat.campaign_id == ctx.campaign.id, PlayerSeat.claim_token == payload.claim_token
        )
    )
    if seat:
        seat.claimed = False
        seat.claim_token = None
        seat.claimed_by = None
        db.commit()
        await broadcast_seats(ctx.campaign.id, db)
    return {"ok": True}


@router.get("/state", response_model=PlayerState)
def player_state(
    ctx: PlayerContext = Depends(get_player_context),
    db: Session = Depends(get_db),
    claim_token: str | None = Query(default=None),
):
    campaign = ctx.campaign
    # A seat the player claimed in-session takes precedence over a per-seat link.
    seat_id = _resolve_seat(db, campaign.id, claim_token) or ctx.seat_id

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
        seat_id=seat_id,
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
