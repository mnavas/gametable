# Installation & Self-Hosting

GameTable runs on your own machine — a home server, a NAS, or a cheap VPS. All you
need is **Docker** and **Docker Compose**. One command brings up the database, the
API, and the web app.

---

## Requirements

- **Docker** 24+ and the **Docker Compose** plugin (`docker compose`, not the old
  `docker-compose`).
- A machine reachable by your players — your LAN for a home game, or a VPS with a
  public address / domain for playing over the internet.
- ~1 GB RAM free is plenty for a small group.

No Python, Node, or PostgreSQL install is needed on the host — it all runs in
containers.

---

## Quick start

```bash
git clone https://github.com/mnavas/gametable.git
cd gametable
cp .env.example .env            # then edit .env (see below)
docker compose up --build
```

On first start the API runs the database migrations automatically
(`alembic upgrade head`) before serving. When the logs settle, open:

- **Web app:** http://localhost:3000
- **API docs:** http://localhost:8001/docs

Register the first account — **the first DM to register becomes the server admin.**

---

## Configuration (`.env`)

Copy `.env.example` to `.env` and adjust:

| Variable | What it does | Notes |
|---|---|---|
| `JWT_SECRET` | Signs DM login tokens | **Change this** to a long random string before real use |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Database credentials | Defaults are fine for a private box; change for a VPS |
| `DB_PORT` | Host port for Postgres | Default `5433` |
| `API_PORT` | Host port for the API | Default `8001` |
| `WEB_PORT` | Host port for the web app | Default `3000` |
| `NEXT_PUBLIC_API_URL` | Where the browser reaches the API | Must be an address your **players'** browsers can reach (see below) |
| `CORS_ORIGINS` | Allowed web origins for the API | Match your web app's address |
| `ALLOW_REGISTRATION` | `open` \| `invite` \| `closed` | After the admin exists, set to `closed` for a single-DM server |

Generate a strong secret:

```bash
openssl rand -hex 32
```

---

## Playing over your LAN or the internet

The **browser** talks to the API directly, so `NEXT_PUBLIC_API_URL` must be an
address your players can reach — not `localhost` (that points at each player's own
machine).

- **LAN:** set `NEXT_PUBLIC_API_URL=http://<your-server-ip>:8001` and
  `CORS_ORIGINS=http://<your-server-ip>:3000`.
- **Internet:** put a reverse proxy (Caddy, nginx, Traefik) with HTTPS in front of
  the web (`:3000`) and API (`:8001`), then set `NEXT_PUBLIC_API_URL` to the API's
  public `https://` URL and `CORS_ORIGINS` to the web app's public URL. HTTPS also
  upgrades the live WebSocket to `wss://` automatically.

Rebuild after changing `.env`:

```bash
docker compose up --build -d
```

---

## Everyday commands

```bash
docker compose up -d          # start in the background
docker compose logs -f api    # follow the API logs
docker compose down           # stop (keeps your data)
docker compose pull && docker compose up --build -d   # update to a new version
```

Your campaigns, maps, and uploaded images live in Docker volumes
(`postgres-data`, `media-data`) and survive restarts and rebuilds.

---

## Backups

Back up the database and the uploaded media:

```bash
# Database
docker compose exec -T db pg_dump -U gametable gametable > gametable-backup.sql

# Uploaded images (maps, tokens, gallery)
docker run --rm -v gametable_media-data:/media -v "$PWD":/out alpine \
  tar czf /out/gametable-media.tgz -C /media .
```

Keep both together — the database references the media files by path.

---

## Troubleshooting

- **Players see "API unreachable" / can't log in** — `NEXT_PUBLIC_API_URL` is set to
  `localhost` or an address they can't reach. Use the server's LAN IP or public URL
  and rebuild.
- **CORS errors in the browser console** — add the exact web-app origin to
  `CORS_ORIGINS` and rebuild.
- **Port already in use** — change `WEB_PORT` / `API_PORT` / `DB_PORT` in `.env`.
- **Migrations didn't run** — they run on API startup; check `docker compose logs api`.
  You can run them by hand with
  `docker compose exec api alembic upgrade head`.

Next: the [DM guide](dm-guide.md) to run your first session, and the
[player guide](player-guide.md) to share with your group.
