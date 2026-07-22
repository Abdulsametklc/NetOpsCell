"""initial ai service schema

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

# NOT: create_type=False sadece postgresql.ENUM (dialect-specific) sinifinda garanti calisir
# (bkz. incident-service 0001 migration'indaki not - generic sa.Enum'da sessizce yok sayilip
# "type already exists" hatasi veriyordu).
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
prediction_method = PGEnum("LLM", "RULE_FALLBACK", name="prediction_method", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    fault_type.create(bind, checkfirst=True)
    priority.create(bind, checkfirst=True)
    suggestion.create(bind, checkfirst=True)
    prediction_method.create(bind, checkfirst=True)

    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("station_code", sa.String(64), nullable=False),
        sa.Column("input_features", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("fault_type", fault_type, nullable=False),
        sa.Column("priority", priority, nullable=False),
        sa.Column("suggestion", suggestion, nullable=False),
        sa.Column("method", prediction_method, nullable=False),
        sa.Column("confidence_explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "accuracy_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_fault_type", fault_type, nullable=False),
        sa.Column("corrected_fault_type", fault_type, nullable=True),
        sa.Column("corrected_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_accuracy_feedback_incident_id", "accuracy_feedback", ["incident_id"])

    op.create_table(
        "team_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("specializations", postgresql.ARRAY(fault_type), nullable=False, server_default="{}"),
        sa.Column("regions", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("base_lat", sa.Float(), nullable=False),
        sa.Column("base_lon", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "team_workload",
        sa.Column(
            "team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("team_profile.id"), primary_key=True
        ),
        sa.Column("active_incident_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "assignment_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_scores", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("chosen_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_assignment_log_incident_id", "assignment_log", ["incident_id"])


def downgrade() -> None:
    op.drop_table("assignment_log")
    op.drop_table("team_workload")
    op.drop_table("team_profile")
    op.drop_table("accuracy_feedback")
    op.drop_table("predictions")

    bind = op.get_bind()
    prediction_method.drop(bind, checkfirst=True)
    suggestion.drop(bind, checkfirst=True)
    priority.drop(bind, checkfirst=True)
    fault_type.drop(bind, checkfirst=True)
