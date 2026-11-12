"""SQLAlchemy ORM models — the GameTable domain.

Visibility is a property of *content*, not of the whole creature. The server is
the enforcement point: hidden_* columns must never be serialized into a player
response (see schemas.py for the role-aware DTOs).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=_now, nullable=False)


# --- Enums ------------------------------------------------------------------

class CreatureType(str, enum.Enum):
    creature = "creature"
    npc = "npc"
    player = "player"


class Visibility(str, enum.Enum):
    hidden = "hidden"            # DM-only
    campaign_public = "campaign_public"  # this campaign's players can see public content
    server_shared = "server_shared"      # public content added to the server bestiary


class NoteVisibility(str, enum.Enum):
    hidden = "hidden"   # DM-only
    public = "public"   # shared handout to players


class RollerType(str, enum.Enum):
    dm = "dm"
    player = "player"


class RollVisibility(str, enum.Enum):
    public = "public"
    private = "private"  # silent — only the roller (and the DM) see it


class ShareKind(str, enum.Enum):
    shared = "shared"  # one link for the whole table
    seat = "seat"      # a per-player link bound to a seat


# --- Core tables ------------------------------------------------------------

class User(Base):
    """A Dungeon Master account. (Players are link-only in v1 — see ShareLink.)"""
    __tablename__ = "users"

    id = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = _created_at()

    campaigns: Mapped[list[Campaign]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # The scene players currently see, and the handout currently pushed (if any).
    active_map_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("maps.id", ondelete="SET NULL"), nullable=True
    )
    active_image_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("gallery_images.id", ondelete="SET NULL"), nullable=True
    )

    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = _created_at()

    owner: Mapped[User] = relationship(back_populates="campaigns")
    maps: Mapped[list[Map]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", foreign_keys="Map.campaign_id"
    )
    creatures: Mapped[list[Creature]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    notes: Mapped[list[Note]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    gallery: Mapped[list[GalleryImage]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", foreign_keys="GalleryImage.campaign_id"
    )
    seats: Mapped[list[PlayerSeat]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    share_links: Mapped[list[ShareLink]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class Map(Base):
    __tablename__ = "maps"

    id = _uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Grid
    grid_type: Mapped[str] = mapped_column(String(20), default="square", nullable=False)  # square|hex|none
    grid_size: Mapped[int] = mapped_column(Integer, default=70, nullable=False)  # px per cell
    grid_offset_x: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    grid_offset_y: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    grid_color: Mapped[str] = mapped_column(String(32), default="#000000", nullable=False)
    unit_per_cell: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)  # e.g. 5 ft

    # Fog of war: list of revealed shapes (polygons/rects) in map coords.
    # DM-only detail; players receive only the derived "revealed" set.
    fog: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at = _created_at()

    campaign: Mapped[Campaign] = relationship(back_populates="maps", foreign_keys=[campaign_id])
    tokens: Mapped[list[Token]] = relationship(back_populates="map", cascade="all, delete-orphan")


class Creature(Base):
    """Reusable library entry: creature / NPC / player character."""
    __tablename__ = "creatures"

    id = _uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default=CreatureType.creature.value, nullable=False)

    token_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # public, shown on click

    public_stats: Mapped[str] = mapped_column(Text, default="", nullable=False)   # rich text, player-visible
    hidden_stats: Mapped[str] = mapped_column(Text, default="", nullable=False)   # DM-only
    hidden_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # DM-only

    visibility: Mapped[str] = mapped_column(String(20), default=Visibility.hidden.value, nullable=False)
    created_at = _created_at()

    campaign: Mapped[Campaign] = relationship(back_populates="creatures")


class Token(Base):
    """A placed instance on a map; usually bound to a Creature."""
    __tablename__ = "tokens"

    id = _uuid_pk()
    map_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("maps.id", ondelete="CASCADE"), index=True, nullable=False
    )
    creature_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("creatures.id", ondelete="SET NULL"), nullable=True
    )
    owner_seat_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("player_seats.id", ondelete="SET NULL"), nullable=True
    )

    label: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # in cells
    rotation: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="#888888", nullable=False)
    border_color: Mapped[str | None] = mapped_column(String(32), nullable=True)

    hidden_from_players: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    z_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at = _created_at()

    map: Mapped[Map] = relationship(back_populates="tokens")
    creature: Mapped[Creature | None] = relationship()


class Note(Base):
    __tablename__ = "notes"

    id = _uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)  # rich text
    visibility: Mapped[str] = mapped_column(String(20), default=NoteVisibility.hidden.value, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at = _created_at()

    campaign: Mapped[Campaign] = relationship(back_populates="notes")


class GalleryImage(Base):
    __tablename__ = "gallery_images"

    id = _uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = _created_at()

    campaign: Mapped[Campaign] = relationship(back_populates="gallery", foreign_keys=[campaign_id])


class PlayerSeat(Base):
    """A player's place at the table. Claimed via a share link, no account needed."""
    __tablename__ = "player_seats"

    id = _uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), default="Player", nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="#3366cc", nullable=False)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = _created_at()

    campaign: Mapped[Campaign] = relationship(back_populates="seats")


class ShareLink(Base):
    """A revocable token that lets a player into a campaign, no account required."""
    __tablename__ = "share_links"

    id = _uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default=ShareKind.shared.value, nullable=False)
    seat_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("player_seats.id", ondelete="SET NULL"), nullable=True
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = _created_at()

    campaign: Mapped[Campaign] = relationship(back_populates="share_links")


class DiceRoll(Base):
    __tablename__ = "dice_rolls"

    id = _uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    roller_type: Mapped[str] = mapped_column(String(10), nullable=False)  # dm|player
    roller_name: Mapped[str] = mapped_column(String(120), nullable=False)
    seat_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("player_seats.id", ondelete="SET NULL"), nullable=True
    )
    formula: Mapped[str] = mapped_column(String(120), nullable=False)       # e.g. "2d6+3"
    detail: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # per-die results
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    visibility: Mapped[str] = mapped_column(String(10), default=RollVisibility.public.value, nullable=False)
    created_at = _created_at()
