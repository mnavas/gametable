"""GameTable API entrypoint."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import (
    auth,
    campaigns,
    creatures,
    gallery,
    maps,
    notes,
    player,
    tokens,
    uploads,
    ws,
)

PUBLIC_MEDIA_DIR = os.path.join(settings.media_dir, "public")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic: run `alembic upgrade head` before starting
    # (docker-compose does this automatically). We only ensure media dirs here.
    os.makedirs(PUBLIC_MEDIA_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.media_dir, "protected"), exist_ok=True)
    yield


app = FastAPI(title="GameTable API", version="0.0.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(campaigns.router)
app.include_router(maps.router)
app.include_router(tokens.router)
app.include_router(creatures.router)
app.include_router(notes.router)
app.include_router(gallery.router)
app.include_router(player.router)
app.include_router(uploads.router)
app.include_router(ws.router)

# Public assets only. DM-only images are served through uploads.py with an
# ownership check — never from this static mount (see REQUIREMENTS §6).
os.makedirs(PUBLIC_MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=PUBLIC_MEDIA_DIR), name="media")


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "gametable-api", "version": app.version}


# Remaining work: Alembic migrations (replace create_all), presence/snapshot on
# WS connect, richer fog geometry, server-shared bestiary copy, and the web client
# (PixiJS map canvas, DM dashboard, player view). See REQUIREMENTS §8–§9.
