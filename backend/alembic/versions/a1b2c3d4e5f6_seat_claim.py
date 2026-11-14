"""Seat claiming: let players pick a character over the shared link.

Adds claim_token (secret proving control of a seat), claimed_by (display name),
and sort_order to player_seats.

Revision ID: a1b2c3d4e5f6
Revises: 589ffd2999d4
Create Date: 2026-11-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "589ffd2999d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("player_seats", sa.Column("claim_token", sa.String(length=64), nullable=True))
    op.add_column("player_seats", sa.Column("claimed_by", sa.String(length=120), nullable=True))
    op.add_column(
        "player_seats",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index(
        op.f("ix_player_seats_claim_token"), "player_seats", ["claim_token"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_player_seats_claim_token"), table_name="player_seats")
    op.drop_column("player_seats", "sort_order")
    op.drop_column("player_seats", "claimed_by")
    op.drop_column("player_seats", "claim_token")
