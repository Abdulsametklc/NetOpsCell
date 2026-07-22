"""initial gamification service schema

Revision ID: 0001
Revises:
Create Date: 2026-07-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# NOT: create_type=False sadece postgresql.ENUM (dialect-specific) sinifinda garanti calisir.
user_level = PGEnum("BRONZ", "GUMUS", "ALTIN", "PLATIN", name="user_level", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    user_level.create(bind, checkfirst=True)

    op.create_table(
        "point_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_point_ledger_user_id", "point_ledger", ["user_id"])

    op.create_table(
        "user_stats",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", user_level, nullable=False, server_default="BRONZ"),
        sa.Column("resolved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_points", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(256), nullable=True),
    )

    op.create_table(
        "user_badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("badge_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("badges.id"), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badges_user_badge"),
    )
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_badges")
    op.drop_table("badges")
    op.drop_table("user_stats")
    op.drop_table("point_ledger")

    bind = op.get_bind()
    user_level.drop(bind, checkfirst=True)
