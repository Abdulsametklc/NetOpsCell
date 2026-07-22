"""initial incident service schema

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

# NOT: create_type=False sadece postgresql.ENUM (dialect-specific) sinifinda garanti
# calisir; generic sa.Enum'da bu bayrak sessizce yok sayilabiliyor ve op.create_table
# ayni tipi tekrar CREATE TYPE ile olusturmaya calisip "already exists" hatasi veriyor.
incident_status = PGEnum(
    "YENI",
    "ATANDI",
    "YOLDA",
    "MUDAHALE_EDILIYOR",
    "PARCA_BEKLENIYOR",
    "COZULDU",
    "KAPANDI",
    name="incident_status",
    create_type=False,
)
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
priority = PGEnum("DUSUK", "ORTA", "YUKSEK", "KRITIK", name="priority", create_type=False)
suggestion = PGEnum("IZLE", "VAKA_AC", "ACIL", name="suggestion", create_type=False)
power_status = PGEnum("NORMAL", "KESINTIDE", name="power_status", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    incident_status.create(bind, checkfirst=True)
    fault_type.create(bind, checkfirst=True)
    priority.create(bind, checkfirst=True)
    suggestion.create(bind, checkfirst=True)
    power_status.create(bind, checkfirst=True)

    op.execute("CREATE SEQUENCE IF NOT EXISTS incident_number_seq START 1")

    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_number", sa.String(32), nullable=False, unique=True),
        sa.Column("station_code", sa.String(64), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("current_status", incident_status, nullable=False, server_default="YENI"),
        sa.Column("fault_type", fault_type, nullable=True),
        sa.Column("priority", priority, nullable=True),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("ai_suggestion", suggestion, nullable=True),
        sa.Column("assigned_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_team_name", sa.String(128), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_manual_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "telemetry_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=True),
        sa.Column("station_code", sa.String(64), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("signal_strength", sa.Float(), nullable=False),
        sa.Column("packet_loss", sa.Float(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("power_status", power_status, nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "incident_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("from_status", incident_status, nullable=True),
        sa.Column("to_status", incident_status, nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "incident_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "incident_resolution_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("technician_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "incident_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False, unique=True
        ),
        sa.Column("noc_operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("is_permanent", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("stars >= 1 AND stars <= 5", name="ck_incident_evaluations_stars_range"),
    )


def downgrade() -> None:
    op.drop_table("incident_evaluations")
    op.drop_table("incident_resolution_notes")
    op.drop_table("incident_messages")
    op.drop_table("incident_status_history")
    op.drop_table("telemetry_readings")
    op.drop_table("incidents")
    op.execute("DROP SEQUENCE IF EXISTS incident_number_seq")

    bind = op.get_bind()
    power_status.drop(bind, checkfirst=True)
    suggestion.drop(bind, checkfirst=True)
    priority.drop(bind, checkfirst=True)
    fault_type.drop(bind, checkfirst=True)
    incident_status.drop(bind, checkfirst=True)
