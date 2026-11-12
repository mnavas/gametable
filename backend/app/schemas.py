"""Pydantic DTOs.

The role-aware split is the heart of the security model: `*DM` schemas expose
everything, `*Public` schemas expose ONLY what a player may see. Player-facing
endpoints and the player WebSocket must serialize with the `*Public` variants so
hidden columns are never sent over the wire.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth -------------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=120)


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    is_admin: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Campaign ---------------------------------------------------------------

class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    active_map_id: uuid.UUID | None = None
    active_image_id: uuid.UUID | None = None


class CampaignOut(ORMModel):
    id: uuid.UUID
    name: str
    description: str
    active_map_id: uuid.UUID | None
    active_image_id: uuid.UUID | None
    archived_at: datetime | None
    created_at: datetime


# --- Creature: DM view vs player (public) view ------------------------------

class CreatureDM(ORMModel):
    id: uuid.UUID
    name: str
    type: str
    token_image_path: str | None
    display_image_path: str | None
    public_stats: str
    hidden_stats: str          # DM-only
    hidden_image_path: str | None  # DM-only
    visibility: str


class CreaturePublic(ORMModel):
    """What a player receives when they click a visible token. No hidden_* fields."""
    id: uuid.UUID
    name: str
    type: str
    token_image_path: str | None
    display_image_path: str | None
    public_stats: str

    @classmethod
    def from_creature(cls, creature) -> "CreaturePublic":
        return cls.model_validate(creature)


# --- Token: DM view vs player view ------------------------------------------

class TokenDM(ORMModel):
    id: uuid.UUID
    map_id: uuid.UUID
    creature_id: uuid.UUID | None
    owner_seat_id: uuid.UUID | None
    label: str
    x: float
    y: float
    size: int
    rotation: float
    color: str
    border_color: str | None
    hidden_from_players: bool
    locked: bool
    z_index: int


class TokenPublic(ORMModel):
    """Players never receive hidden tokens at all; this is for visible ones."""
    id: uuid.UUID
    creature_id: uuid.UUID | None
    owner_seat_id: uuid.UUID | None
    label: str
    x: float
    y: float
    size: int
    rotation: float
    color: str
    border_color: str | None
    z_index: int


# --- Map: DM view vs player view --------------------------------------------

class MapDM(ORMModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    name: str
    image_path: str
    width: int
    height: int
    grid_type: str
    grid_size: int
    grid_offset_x: int
    grid_offset_y: int
    grid_color: str
    unit_per_cell: float
    fog: dict            # full fog shapes — DM only
    sort_order: int


class MapPublic(ORMModel):
    """Players get the map + the revealed fog regions (what to show)."""
    id: uuid.UUID
    name: str
    image_path: str
    width: int
    height: int
    grid_type: str
    grid_size: int
    grid_offset_x: int
    grid_offset_y: int
    grid_color: str
    unit_per_cell: float
    fog: dict  # NOTE: the player serializer passes only the "revealed" set, not hidden hints


# --- Map updates & fog ------------------------------------------------------

class MapUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    grid_type: str | None = None
    grid_size: int | None = Field(default=None, ge=0)
    grid_offset_x: int | None = None
    grid_offset_y: int | None = None
    grid_color: str | None = None
    unit_per_cell: float | None = None
    sort_order: int | None = None


class FogUpdate(BaseModel):
    op: str  # "reveal" | "hide" | "reset"
    shape: dict | None = None  # polygon/rect in map coords; None for reset


# --- Token create / update --------------------------------------------------

class TokenCreate(BaseModel):
    creature_id: uuid.UUID | None = None
    owner_seat_id: uuid.UUID | None = None
    label: str = ""
    x: float = 0.0
    y: float = 0.0
    size: int = 1
    rotation: float = 0.0
    color: str = "#888888"
    border_color: str | None = None
    hidden_from_players: bool = False
    locked: bool = False
    z_index: int = 0


class TokenUpdate(BaseModel):
    label: str | None = None
    x: float | None = None
    y: float | None = None
    size: int | None = None
    rotation: float | None = None
    color: str | None = None
    border_color: str | None = None
    hidden_from_players: bool | None = None
    locked: bool | None = None
    z_index: int | None = None
    owner_seat_id: uuid.UUID | None = None


# --- Creature create / update -----------------------------------------------

class CreatureCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = "creature"
    public_stats: str = ""
    hidden_stats: str = ""
    visibility: str = "hidden"


class CreatureUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    type: str | None = None
    public_stats: str | None = None
    hidden_stats: str | None = None
    visibility: str | None = None


# --- Notes ------------------------------------------------------------------

class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = ""
    visibility: str = "hidden"
    sort_order: int = 0


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    body: str | None = None
    visibility: str | None = None
    sort_order: int | None = None


class NoteDM(ORMModel):
    id: uuid.UUID
    title: str
    body: str
    visibility: str
    sort_order: int


class NotePublic(ORMModel):
    id: uuid.UUID
    title: str
    body: str


# --- Gallery ----------------------------------------------------------------

class GalleryImageOut(ORMModel):
    id: uuid.UUID
    name: str
    image_path: str
    is_shared: bool
    created_at: datetime


# --- Player composite view --------------------------------------------------

class PlayerState(BaseModel):
    campaign_name: str
    active_map: MapPublic | None
    tokens: list[TokenPublic]
    active_image: GalleryImageOut | None
    seat_id: uuid.UUID | None


# --- Dice -------------------------------------------------------------------

class RollRequest(BaseModel):
    formula: str = Field(min_length=1, max_length=120)  # e.g. "2d20+5", "1d8-1"
    visibility: str = "public"  # public | private


class PlayerRollRequest(RollRequest):
    player_name: str = Field(default="Player", max_length=120)


class DiceRollOut(ORMModel):
    id: uuid.UUID
    roller_type: str
    roller_name: str
    formula: str
    detail: dict
    total: int
    visibility: str
    created_at: datetime


# --- Share links ------------------------------------------------------------

class ShareLinkCreate(BaseModel):
    label: str = ""
    kind: str = "shared"  # shared | seat
    seat_id: uuid.UUID | None = None
    password: str | None = None
    expires_at: datetime | None = None


class ShareLinkOut(ORMModel):
    id: uuid.UUID
    token: str
    label: str
    kind: str
    seat_id: uuid.UUID | None
    revoked: bool
    expires_at: datetime | None
    created_at: datetime
