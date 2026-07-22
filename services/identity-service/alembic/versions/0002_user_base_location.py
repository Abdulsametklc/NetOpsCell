"""add base_lat/base_lon to users (needed for identity.personnel.upserted event
-> ai-service team_profile Haversine distance scoring, ARCHITECTURE.md §7)

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("base_lat", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("base_lon", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "base_lon")
    op.drop_column("users", "base_lat")
