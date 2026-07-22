"""CP5: rozet sayaclari + tekrar-ariza/uzmanlik takip tablolari

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

fault_type = PGEnum(
    "DONANIM",
    "GUC_KESINTISI",
    "BAGLANTI",
    "YAZILIM",
    "ISINMA",
    "BELIRSIZ",
    name="fault_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    fault_type.create(bind, checkfirst=True)

    op.add_column("user_stats", sa.Column("fast_resolution_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "user_stats", sa.Column("critical_within_sla_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "user_stats", sa.Column("clean_resolution_streak", sa.Integer(), nullable=False, server_default="0")
    )

    op.create_table(
        "station_resolution_log",
        sa.Column("station_code", sa.String(64), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "fault_type_resolution_counts",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fault_type", fault_type, primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("fault_type_resolution_counts")
    op.drop_table("station_resolution_log")

    op.drop_column("user_stats", "clean_resolution_streak")
    op.drop_column("user_stats", "critical_within_sla_count")
    op.drop_column("user_stats", "fast_resolution_count")

    bind = op.get_bind()
    fault_type.drop(bind, checkfirst=True)
