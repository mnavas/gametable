"""Live table sync over WebSocket.

Two entry points share one hub per campaign:
  /ws/dm?campaign_id=...&token=<jwt>     — full-trust DM channel
  /ws/player?share_token=...             — player channel, public events only

Incoming messages from a player are validated against their permissions before
being applied/rebroadcast (e.g. a player may move only their own token). This
file wires the transport; message handlers are intentionally thin stubs to be
filled as the map/token endpoints land (see TODO markers).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Campaign, GalleryImage, Map, PlayerSeat, ShareLink, Token, User
from ..realtime import Connection, hub
from ..schemas import GalleryImageOut, MapDM, MapPublic, TokenDM, TokenPublic
from ..security import decode_access_token

router = APIRouter(tags=["realtime"])


def build_snapshot(db: Session, campaign: Campaign, is_dm: bool) -> dict:
    """Role-filtered 'here is the current board' message sent right after connect.

    Uses the same filtering as live events, so a reconnecting player can never
    see more than they could live (no hidden tokens, revealed fog only).
    """
    data: dict = {"type": "state", "map": None, "tokens": [], "active_image": None}

    if campaign.active_map_id:
        m = db.get(Map, campaign.active_map_id)
        if m:
            if is_dm:
                data["map"] = MapDM.model_validate(m).model_dump(mode="json")
                toks = db.scalars(select(Token).where(Token.map_id == m.id).order_by(Token.z_index)).all()
                data["tokens"] = [TokenDM.model_validate(t).model_dump(mode="json") for t in toks]
            else:
                mp = MapPublic.model_validate(m).model_dump(mode="json")
                mp["fog"] = {"revealed": (m.fog or {}).get("revealed", [])}
                data["map"] = mp
                toks = db.scalars(
                    select(Token).where(Token.map_id == m.id, Token.hidden_from_players.is_(False)).order_by(Token.z_index)
                ).all()
                data["tokens"] = [TokenPublic.model_validate(t).model_dump(mode="json") for t in toks]

    if campaign.active_image_id:
        img = db.get(GalleryImage, campaign.active_image_id)
        if img:
            data["active_image"] = GalleryImageOut.model_validate(img).model_dump(mode="json")

    return data


@router.websocket("/ws/dm")
async def dm_socket(websocket: WebSocket, campaign_id: uuid.UUID, token: str = Query(...)):
    subject = decode_access_token(token)
    if not subject:
        await websocket.close(code=4401)
        return
    with SessionLocal() as db:
        user = db.get(User, uuid.UUID(subject))
        campaign = db.get(Campaign, campaign_id)
        if not user or not campaign or campaign.owner_id != user.id:
            await websocket.close(code=4403)
            return
        dm_name = user.display_name
        snapshot = build_snapshot(db, campaign, is_dm=True)

    conn = Connection(ws=websocket, is_dm=True, name=dm_name, color="#f0c060")
    await hub.connect(campaign_id, conn)
    await websocket.send_json(snapshot)
    await hub.broadcast_presence(campaign_id)
    try:
        await _pump(campaign_id, conn)
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(campaign_id, conn)
        await hub.broadcast_presence(campaign_id)


@router.websocket("/ws/player")
async def player_socket(websocket: WebSocket, share_token: str = Query(...)):
    with SessionLocal() as db:
        link = db.scalar(select(ShareLink).where(ShareLink.token == share_token))
        if not link or link.revoked:
            await websocket.close(code=4404)
            return
        if link.expires_at and link.expires_at < datetime.now(timezone.utc):
            await websocket.close(code=4410)
            return
        campaign_id = link.campaign_id
        seat_id = link.seat_id
        seat_name = None
        if seat_id:
            seat = db.get(PlayerSeat, seat_id)
            seat_name = seat.name if seat else None
        campaign = db.get(Campaign, campaign_id)
        snapshot = build_snapshot(db, campaign, is_dm=False)

    conn = Connection(ws=websocket, is_dm=False, seat_id=seat_id, name=seat_name or "Player")
    await hub.connect(campaign_id, conn)
    await websocket.send_json(snapshot)
    await hub.broadcast_presence(campaign_id)
    try:
        await _pump(campaign_id, conn)
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(campaign_id, conn)
        await hub.broadcast_presence(campaign_id)


async def _pump(campaign_id: uuid.UUID, conn: Connection) -> None:
    """Receive client messages and route them. See WEBSOCKET_PROTOCOL.md."""
    while True:
        msg = await conn.ws.receive_json()
        mtype = msg.get("type")

        if mtype == "ping":
            # Transient pointer ping — broadcast to everyone.
            await hub.broadcast(campaign_id, {"type": "ping", "x": msg.get("x"), "y": msg.get("y")})

        elif mtype == "presence":
            # A viewer set their display name / color.
            name = msg.get("name")
            if isinstance(name, str) and name.strip():
                conn.name = name.strip()[:120]
            color = msg.get("color")
            if isinstance(color, str):
                conn.color = color[:32]
            await hub.broadcast_presence(campaign_id)

        elif mtype == "token_move":
            await _handle_token_move(campaign_id, conn, msg)

        # Other inbound types (fog_update, token_create/delete) are DM-only and go
        # through the REST routers, which persist and then broadcast. The socket
        # accepts only the live-drag + ping fast paths here.


async def _handle_token_move(campaign_id: uuid.UUID, conn: Connection, msg: dict) -> None:
    """Persist a drag and rebroadcast, enforcing player permissions."""
    raw_id = msg.get("token_id")
    x, y = msg.get("x"), msg.get("y")
    if raw_id is None or x is None or y is None:
        return
    try:
        token_id = uuid.UUID(str(raw_id))
    except ValueError:
        return

    with SessionLocal() as db:
        token = db.get(Token, token_id)
        if not token:
            return
        m = db.get(Map, token.map_id)
        if not m or m.campaign_id != campaign_id:
            return  # token isn't in this campaign

        # Authorization: a player may move only their own, unlocked token.
        if not conn.is_dm:
            if token.locked or token.owner_seat_id is None or token.owner_seat_id != conn.seat_id:
                return

        token.x = float(x)
        token.y = float(y)
        db.commit()
        db.refresh(token)
        hidden = token.hidden_from_players
        dm_payload = {"type": "token_move", "token": TokenDM.model_validate(token).model_dump(mode="json")}
        player_payload = {"type": "token_move", "token": TokenPublic.model_validate(token).model_dump(mode="json")}

    # Hidden tokens never leak to players.
    if hidden:
        await hub.broadcast(campaign_id, dm_payload, dm_only=True)
    else:
        await hub.broadcast(campaign_id, dm_payload, player_payload=player_payload)
