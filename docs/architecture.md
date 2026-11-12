# Architecture

A map of how GameTable is put together, for contributors. For the full product spec
see [REQUIREMENTS.md](../REQUIREMENTS.md); for the live-sync message contract see
[WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md).

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js (App Router, TypeScript); the tabletop is a Canvas 2D renderer |
| Backend | FastAPI (Python), SQLAlchemy 2.0, Pydantic v2 |
| Realtime | Native FastAPI WebSockets |
| Database | PostgreSQL, migrations via Alembic |
| Auth | JWT (DMs) + argon2 password hashing; players use revocable share tokens |
| Packaging | Docker Compose (`db`, `api`, `web`) |

```
web/        Next.js app ── REST + WebSocket ──▶ backend/  FastAPI ──▶ PostgreSQL
                                                   └── media volume (images)
```

---

## Layout

```
backend/app/
  models.py      SQLAlchemy domain (users, campaigns, maps, tokens, creatures,
                 notes, gallery_images, player_seats, share_links, dice_rolls)
  schemas.py     Pydantic DTOs — the role-aware split (see below)
  security.py    argon2 hashing, JWT, share-token generation, the dice roller
  deps.py        Request gates: DM auth, campaign ownership, share-token context
  realtime.py    In-process WebSocket hub — per-campaign fan-out + permission filter
  storage.py     Public vs protected (DM-only) media buckets
  routers/       auth, campaigns, maps, tokens, creatures, notes, gallery,
                 player, uploads, ws
  alembic/       Migrations (initial schema + future revisions)
web/
  lib/           api.ts (REST client), useWS.ts (reconnecting socket), types.ts
  components/    TableCanvas, DicePanel, CreatureEditor
  app/           login, register, campaigns (dashboard + DM session), play/[token]
```

---

## The security model (read this before touching serialization)

**Visibility is a property of content, not of the whole creature.** A creature can
have public art and stats *and* a DM-only block and image at the same time.

Enforcement lives in **two layers**, both server-side:

1. **Role-aware schemas** (`schemas.py`). Every entity has a `*DM` DTO (everything)
   and a `*Public` DTO (player-safe). Player-facing endpoints and the player
   WebSocket serialize with the `*Public` variants, so hidden columns are never put
   on the wire — not merely hidden in the UI.
2. **The WebSocket hub** (`realtime.py`). It fans out each event per connection: the
   DM gets everything; players get a filtered payload, or nothing. Hidden tokens,
   hidden fog shapes, and private rolls are dropped for player connections.

Rules that must always hold (also listed in WEBSOCKET_PROTOCOL.md):

- Never serialize `hidden_*` fields to a player.
- Hidden tokens and hidden fog are **omitted** from player payloads, not flagged.
- Private (silent) rolls broadcast DM-only.
- Player-originated writes (e.g. moving a token) are authorized server-side (own,
  unlocked token) before persist + rebroadcast.
- The **snapshot sent on connect** uses the same role filter as live events, so a
  reconnecting player can't see more than they could live.

> v1 note: the map image itself is delivered to players and fog is applied in the
> browser. True "player can't fetch the hidden image" fog needs server-side tiling —
> a documented trade-off, fine for a home game.

---

## Data model (core relationships)

```
User (DM) ──< Campaign ──< Map ──< Token >── Creature
                   ├──< Note
                   ├──< GalleryImage        (active_image_id → pushed handout)
                   ├──< PlayerSeat
                   ├──< ShareLink           (player entry, revocable)
                   └──< DiceRoll
         Campaign.active_map_id → Map        (the scene players currently see)
```

The `campaigns ↔ maps / gallery_images` cycle (`active_map_id`, `active_image_id`)
is created with `use_alter=True` so Alembic can order the migration.

---

## Realtime

The server is authoritative. Two WebSocket entry points share one hub per campaign:

- `GET /ws/dm?campaign_id=…&token=<jwt>` — full-trust DM channel.
- `GET /ws/player?share_token=…` — player channel, public events only.

On connect each side receives a role-filtered `state` snapshot, then live events
(`token_move`, `token_upsert`, `token_delete`, `fog`, `active_map`, `active_image`,
`dice_roll`, `presence`). See [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md).

The hub is in-process; for a multi-worker deployment, back the fan-out with Redis
pub/sub.

---

## Working on it

```bash
# Whole stack
docker compose up --build

# Backend only (needs a running Postgres and DATABASE_URL)
cd backend && pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend only
cd web && npm install && npm run dev
```

Adding a model or column? Create a migration — don't rely on auto-create:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Keep the role-aware schemas honest: a new field on a creature/token/map must be
added to the `*DM` DTO, and to the `*Public` DTO **only if players may see it**.
