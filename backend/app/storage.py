"""Media storage: public assets vs DM-only (protected) assets.

Public assets (maps, token/display images, gallery) live under
`<media>/public/<campaign_id>/` and are served by the static mount at `/media`.
Protected assets (a creature's hidden image) live under
`<media>/protected/<campaign_id>/` and are served ONLY through an authorized
endpoint (see routers/uploads.py). DB columns store the servable URL path.
"""
from __future__ import annotations

import os
import uuid

from fastapi import HTTPException, UploadFile, status

from .config import settings

_ALLOWED = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_MAX_BYTES = 25 * 1024 * 1024  # 25 MB


def _public_root() -> str:
    return os.path.join(settings.media_dir, "public")


def _protected_root() -> str:
    return os.path.join(settings.media_dir, "protected")


def protected_fs_path(campaign_id: uuid.UUID, filename: str) -> str:
    return os.path.join(_protected_root(), str(campaign_id), filename)


def _save(file: UploadFile, dest_dir: str) -> str:
    ext = _ALLOWED.get(file.content_type or "")
    if not ext:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PNG/JPEG/WebP/GIF images allowed")
    data = file.file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image too large (max 25 MB)")
    os.makedirs(dest_dir, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(dest_dir, name), "wb") as fh:
        fh.write(data)
    return name


def save_public(file: UploadFile, campaign_id: uuid.UUID) -> str:
    """Save and return the servable URL path, e.g. '/media/<cid>/<file>'."""
    name = _save(file, os.path.join(_public_root(), str(campaign_id)))
    return f"/media/{campaign_id}/{name}"


def save_protected(file: UploadFile, campaign_id: uuid.UUID) -> str:
    """Save a DM-only image; returns '/media-protected/<cid>/<file>'."""
    name = _save(file, os.path.join(_protected_root(), str(campaign_id)))
    return f"/media-protected/{campaign_id}/{name}"
