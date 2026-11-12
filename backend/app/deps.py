"""FastAPI dependencies: authenticate a DM, or resolve a player's share token."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Campaign, Creature, Map, ShareLink, Token
from .security import decode_access_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Resolve the logged-in DM from a Bearer token."""
    from .models import User

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1]
    subject = decode_access_token(token)
    if not subject:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, uuid.UUID(subject))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def get_owned_campaign(
    campaign_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Campaign:
    """Fetch a campaign and assert the current DM owns it (no IDOR)."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign or campaign.owner_id != user.id:
        # 404 (not 403) so we don't leak existence of other DMs' campaigns.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    return campaign


def get_owned_map(
    map_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Map:
    m = db.get(Map, map_id)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Map not found")
    campaign = db.get(Campaign, m.campaign_id)
    if not campaign or campaign.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Map not found")
    return m


def get_owned_token(
    token_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Token:
    t = db.get(Token, token_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Token not found")
    m = db.get(Map, t.map_id)
    campaign = db.get(Campaign, m.campaign_id) if m else None
    if not campaign or campaign.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Token not found")
    return t


def get_owned_creature(
    creature_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Creature:
    c = db.get(Creature, creature_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creature not found")
    campaign = db.get(Campaign, c.campaign_id)
    if not campaign or campaign.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creature not found")
    return c


@dataclass
class PlayerContext:
    """The resolved, authorized context for a link-only player."""
    campaign: Campaign
    share_link: ShareLink
    seat_id: uuid.UUID | None


def get_player_context(
    share_token: str = Query(..., description="Player share token from the link"),
    db: Session = Depends(get_db),
) -> PlayerContext:
    """Resolve a player's share token into a campaign scope. Public data only.

    This is the single gate for every player-facing endpoint and WebSocket.
    """
    link = db.scalar(select(ShareLink).where(ShareLink.token == share_token))
    if not link or link.revoked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid share link")
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_410_GONE, "Share link expired")
    campaign = db.get(Campaign, link.campaign_id)
    if not campaign:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    return PlayerContext(campaign=campaign, share_link=link, seat_id=link.seat_id)
