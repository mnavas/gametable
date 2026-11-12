"""In-process WebSocket hub, grouped by campaign.

The hub is the permission gate for live sync: the DM connection receives every
event; player connections receive only events marked player-visible. For a
multi-worker deployment, back this with Redis pub/sub later (see REQUIREMENTS §7).
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class Connection:
    ws: WebSocket
    is_dm: bool
    seat_id: uuid.UUID | None = None


@dataclass
class Room:
    connections: list[Connection] = field(default_factory=list)


class Hub:
    def __init__(self) -> None:
        self._rooms: dict[uuid.UUID, Room] = {}
        self._lock = asyncio.Lock()

    async def connect(self, campaign_id: uuid.UUID, conn: Connection) -> None:
        await conn.ws.accept()
        async with self._lock:
            self._rooms.setdefault(campaign_id, Room()).connections.append(conn)

    async def disconnect(self, campaign_id: uuid.UUID, conn: Connection) -> None:
        async with self._lock:
            room = self._rooms.get(campaign_id)
            if room and conn in room.connections:
                room.connections.remove(conn)
            if room and not room.connections:
                self._rooms.pop(campaign_id, None)

    async def broadcast(
        self,
        campaign_id: uuid.UUID,
        message: dict | None,
        *,
        dm_only: bool = False,
        player_payload: dict | None = None,
    ) -> None:
        """Fan out an event.

        - `message`: sent to DM connections (None → send nothing to DMs).
        - `dm_only=True`: players receive nothing (e.g. a private roll, a
          hidden-token move the players must not see).
        - `player_payload`: players receive this filtered payload instead of
          `message` (e.g. a token's public fields only). Falls back to `message`.
        """
        room = self._rooms.get(campaign_id)
        if not room:
            return
        player_msg = player_payload if player_payload is not None else message
        dead: list[Connection] = []
        for conn in list(room.connections):
            try:
                if conn.is_dm:
                    if message is not None:
                        await conn.ws.send_json(message)
                elif not dm_only and player_msg is not None:
                    await conn.ws.send_json(player_msg)
            except Exception:
                dead.append(conn)
        for conn in dead:
            await self.disconnect(campaign_id, conn)


hub = Hub()
