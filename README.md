# GameTable

Self-hosted virtual tabletop (VTT) for D&D — in the spirit of Owlbear Rodeo, but you
run it on your own server. Each Dungeon Master gets an account and keeps their
campaigns, maps, creature library, notes, and gallery private. Players join a
campaign through a share link (no account needed), see the fog-obscured map with live
tokens, click tokens for public info, view handouts the DM pushes, and roll dice in a
shared log (publicly or silently).

**Website:** https://mnavas.github.io/gametable/ · **Docs:** [installation](docs/installation.md)
· [DM guide](docs/dm-guide.md) · [player guide](docs/player-guide.md) · [architecture](docs/architecture.md)

## Status

Working app. Backend (auth, campaigns, maps + fog, tokens, creatures with
public/hidden stats & images, notes, gallery handouts, share links, dice,
WebSocket snapshot + presence) and web client (DM dashboard, map canvas, creature
editor, player view) are built and tested; schema managed by Alembic.

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
    storage.py      Public vs protected (DM-only) media buckets
    bundle.py       Export/import a campaign as a .zip (+ `python -m app.bundle pack`)
    routers/        auth, campaigns, maps, tokens, creatures, notes, gallery,
                    player, uploads, ws, bundle
    alembic/        Database migrations
web/                Next.js (TypeScript) app
  lib/              api.ts, useWS.ts, types.ts
  components/       TableCanvas, DicePanel, CreatureEditor
  app/              login, register, campaigns/[id] (DM), play/[token] (player)
content/adventures/ Ready-to-import adventures (incl. a free CC BY 4.0 one-shot)
docs/               installation, dm-guide, player-guide, architecture, protocol, bundle format
index.html          Landing page (GitHub Pages)
```

## Highlights

- Self-hosted (Docker Compose / single box), multi-DM with secured login
- Campaigns → maps, tokens, reusable creatures/NPCs/players, notes, gallery
- Manual fog of war; players see only what the DM reveals
- Public vs DM-only (hidden) creature stats and notes, enforced server-side
- Player share link → player view (map mode + handout/gallery mode)
- Shared dice roller with public and private/silent rolls
- Live WebSocket sync with server-side permission filtering
- **Export / import a campaign as a `.zip`** — build it at home, run it at the table
- A **free, ready-to-run one-shot** included (CC BY 4.0, SRD-only)

## A free adventure, included

[`content/adventures/the-sunless-shrine/`](content/adventures/the-sunless-shrine) is a
complete **Dungeons & Dragons 5e one-shot** (four 2nd-level PCs, ~2–3 hours) with an
original battlemap, tokens, player handouts, SRD stat blocks, and full DM notes.
Import `content/adventures/the-sunless-shrine.zip` (**Campaigns → Import bundle**) and
run it. Text and art are **CC BY 4.0**; rules use the **SRD 5.1** under CC BY 4.0 —
see the adventure's [NOTICE](content/adventures/the-sunless-shrine/NOTICE.md).

## Documentation

- [Installation & self-hosting](docs/installation.md) — Docker, env, LAN/internet, backups
- [DM guide](docs/dm-guide.md) — run a session end to end
- [Player guide](docs/player-guide.md) — joining via the share link
- [Bundle format](docs/BUNDLE_FORMAT.md) — export/import, and how to author a `.zip` by hand
- [Architecture](docs/architecture.md) and [WebSocket protocol](docs/WEBSOCKET_PROTOCOL.md) — for contributors

## Support

GameTable is a free, open-source side project. If it helps your group, you can
support it via [GitHub Sponsors](https://github.com/sponsors/mnavas),
[PayPal](https://paypal.me/warionv), or the De Una QR on the
[website](https://mnavas.github.io/gametable/#support).

## License

[MIT](LICENSE).
