"""Authorized serving of DM-only (protected) media.

Public media is served by the static mount at /media. Protected media (e.g. a
creature's hidden image) is served only here, and only to the owning DM.
"""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import storage
from ..database import get_db
from ..deps import get_current_user
from ..models import Campaign

router = APIRouter(tags=["media"])


@router.get("/media-protected/{campaign_id}/{filename}")
def get_protected_media(
    campaign_id: uuid.UUID,
    filename: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Only the campaign owner may fetch its protected assets.
    campaign = db.get(Campaign, campaign_id)
    if not campaign or campaign.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")

    # Guard against path traversal.
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bad filename")

    path = storage.protected_fs_path(campaign_id, filename)
    if not os.path.isfile(path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return FileResponse(path)
