# GameTable

Self-hosted virtual tabletop (VTT) for D&D — in the spirit of Owlbear Rodeo, but you
run it on your own server. Each Dungeon Master gets an account and keeps their
campaigns, maps, creature library, notes, and gallery private. Players join a
campaign through a share link (no account needed), see the fog-obscured map with live
tokens, click tokens for public info, view handouts the DM pushes, and roll dice in a
shared log (publicly or silently).

See [REQUIREMENTS.md](REQUIREMENTS.md) for the full feature spec, domain model,
permissions matrix, proposed stack, and phased roadmap.

## Status

Early scaffold. Requirements drafted; backend/web skeleton in place (auth,
campaigns, share links, dice, WebSocket gate). Maps/tokens/creatures/notes/gallery
routers and the map canvas are the next slices.

## Stack

FastAPI + PostgreSQL + Next.js, in Docker (mirrors QuizBuilder). Realtime over
native FastAPI WebSockets; hidden-vs-public content enforced in the API serializer.

## Getting started (dev)

```bash
cp .env.example .env          # then edit JWT_SECRET
docker compose up --build     # db :5433, api :8001, web :3000
```

- API docs: http://localhost:8001/docs
- Web stub: http://localhost:3000 (shows API health)
- First registered account becomes the server admin.

The schema is managed by **Alembic**; `docker compose` runs `alembic upgrade head`
before the API starts. For a non-Docker run, apply migrations first:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://gametable:gametable@localhost:5433/gametable \
  alembic upgrade head
```

## Layout

```
backend/            FastAPI service
  app/
    models.py       SQLAlchemy domain (users, campaigns, maps, tokens, creatures,
                    notes, gallery, seats, share_links, dice_rolls)
    schemas.py      Role-aware DTOs — *DM (full) vs *Public (player-safe)
    security.py     argon2 hashing, JWT, share tokens, dice roller
    deps.py         DM auth + share-token (player) access gates
    realtime.py     WebSocket hub — per-campaign fan-out + permission filter
    routers/        auth, campaigns (+share links, dice), ws
web/                Next.js (TypeScript) stub — tabletop canvas goes here
docs/
  WEBSOCKET_PROTOCOL.md   Live sync message contract
```

## Highlights

- Self-hosted (Docker Compose / single box), multi-DM with secured login
- Campaigns → maps, tokens, reusable creatures/NPCs/players, notes, gallery
- Manual fog of war; players see only what the DM reveals
- Public vs DM-only (hidden) creature stats and notes, enforced server-side
- Player share link → player view (map mode + handout/gallery mode)
- Shared dice roller with public and private/silent rolls
- Live WebSocket sync with server-side permission filtering
