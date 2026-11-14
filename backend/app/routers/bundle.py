"""Export a campaign to a .zip bundle, and import one into a new campaign.

Portability use case: a DM builds a campaign at home, exports it, carries the
.zip to the game, and imports it on the server at the table.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import bundle as bundle_svc
from ..database import get_db
from ..deps import get_current_user, get_owned_campaign
from ..models import Campaign
from ..schemas import CampaignOut

router = APIRouter(tags=["bundle"])

_MAX_UPLOAD = 200 * 1024 * 1024  # 200 MB


def _filename(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "campaign"
    return f"{slug}.gtbundle.zip"


@router.get("/campaigns/{campaign_id}/export")
def export_campaign(
    campaign: Campaign = Depends(get_owned_campaign),
    db: Session = Depends(get_db),
):
    data = bundle_svc.export_campaign(db, campaign)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{_filename(campaign.name)}"'},
    )


@router.post("/campaigns/import", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def import_campaign(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    data = await file.read()
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Bundle too large")
    try:
        campaign = bundle_svc.import_bundle(db, user, data, name_override=name)
    except bundle_svc.BundleError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    return campaign
