"""Tokens: place, move, update, delete — with role-filtered live events."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_owned_map, get_owned_token
from ..models import Map, Token
from ..realtime import hub
from ..schemas import TokenCreate, TokenDM, TokenPublic, TokenUpdate

router = APIRouter(tags=["tokens"])


async def _broadcast_upsert(db: Session, token: Token) -> None:
    """Send the full token to the DM; send the public token to players unless hidden."""
    m = db.get(Map, token.map_id)
    if not m:
        return
    dm_event = {"type": "token_upsert", "token": TokenDM.model_validate(token).model_dump(mode="json")}
    if token.hidden_from_players:
        await hub.broadcast(m.campaign_id, dm_event, dm_only=True)
    else:
        player_event = {
            "type": "token_upsert",
            "token": TokenPublic.model_validate(token).model_dump(mode="json"),
        }
        await hub.broadcast(m.campaign_id, dm_event, player_payload=player_event)


@router.get("/maps/{map_id}/tokens", response_model=list[TokenDM])
def list_tokens(m: Map = Depends(get_owned_map), db: Session = Depends(get_db)):
    return db.scalars(select(Token).where(Token.map_id == m.id).order_by(Token.z_index)).all()


@router.post("/maps/{map_id}/tokens", response_model=TokenDM, status_code=status.HTTP_201_CREATED)
async def create_token(
    payload: TokenCreate, m: Map = Depends(get_owned_map), db: Session = Depends(get_db)
):
    token = Token(map_id=m.id, **payload.model_dump())
    db.add(token)
    db.commit()
    db.refresh(token)
    await _broadcast_upsert(db, token)
    return token


@router.patch("/tokens/{token_id}", response_model=TokenDM)
async def update_token(
    payload: TokenUpdate, token: Token = Depends(get_owned_token), db: Session = Depends(get_db)
):
    was_hidden = token.hidden_from_players
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(token, key, value)
    db.commit()
    db.refresh(token)

    # If a token just became hidden, tell players (only) to remove it.
    m = db.get(Map, token.map_id)
    if m and was_hidden is False and token.hidden_from_players is True:
        await hub.broadcast(
            m.campaign_id,
            None,  # nothing new for the DM
            player_payload={"type": "token_delete", "token_id": str(token.id)},
        )
    await _broadcast_upsert(db, token)
    return token


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_token(token: Token = Depends(get_owned_token), db: Session = Depends(get_db)):
    m = db.get(Map, token.map_id)
    campaign_id = m.campaign_id if m else None
    token_id = str(token.id)
    db.delete(token)
    db.commit()
    if campaign_id:
        await hub.broadcast(campaign_id, {"type": "token_delete", "token_id": token_id})
