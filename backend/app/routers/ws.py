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

from ..database import SessionLocal
from ..models import Campaign, Map, ShareLink, Token, User
from ..realtime import Connection, hub
from ..schemas import TokenDM, TokenPublic
from ..security import decode_access_token

router = APIRouter(tags=["realtime"])


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

    conn = Connection(ws=websocket, is_dm=True)
    await hub.connect(campaign_id, conn)
    try:
        await _pump(campaign_id, conn)
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(campaign_id, conn)


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

    conn = Connection(ws=websocket, is_dm=False, seat_id=seat_id)
    await hub.connect(campaign_id, conn)
    try:
        await _pump(campaign_id, conn)
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(campaign_id, conn)


async def _pump(campaign_id: uuid.UUID, conn: Connection) -> None:
    """Receive client messages and route them. See WEBSOCKET_PROTOCOL.md."""
    while True:
        msg = await conn.ws.receive_json()
        mtype = msg.get("type")

        if mtype == "ping":
            # Transient pointer ping — broadcast to everyone.
            await hub.broadcast(campaign_id, {"type": "ping", "x": msg.get("x"), "y": msg.get("y")})

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
