import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.schemas.contracts import FaultType, IncidentStatus, PowerStatus, Priority, Suggestion


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_number: Mapped[str] = mapped_column(sa.String(32), unique=True, nullable=False)
    station_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    current_status: Mapped[IncidentStatus] = mapped_column(
        sa.Enum(IncidentStatus, name="incident_status"), nullable=False, default=IncidentStatus.YENI
    )
    fault_type: Mapped[FaultType | None] = mapped_column(sa.Enum(FaultType, name="fault_type"), nullable=True)
    priority: Mapped[Priority | None] = mapped_column(sa.Enum(Priority, name="priority"), nullable=True)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_suggestion: Mapped[Suggestion | None] = mapped_column(sa.Enum(Suggestion, name="suggestion"), nullable=True)

    assigned_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_team_name: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)

    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_status: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="ACTIVE")

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    telemetry_readings: Mapped[list["TelemetryReading"]] = relationship(back_populates="incident")
    status_history: Mapped[list["IncidentStatusHistory"]] = relationship(back_populates="incident")
    messages: Mapped[list["IncidentMessage"]] = relationship(back_populates="incident")
    resolution_notes: Mapped[list["IncidentResolutionNote"]] = relationship(back_populates="incident")
    evaluation: Mapped["IncidentEvaluation | None"] = relationship(back_populates="incident", uselist=False)


class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=True
    )
    station_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False)
    packet_loss: Mapped[float] = mapped_column(Float, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    power_status: Mapped[PowerStatus] = mapped_column(sa.Enum(PowerStatus, name="power_status"), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident | None"] = relationship(back_populates="telemetry_readings")


class IncidentStatusHistory(Base):
    __tablename__ = "incident_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    from_status: Mapped[IncidentStatus | None] = mapped_column(
        sa.Enum(IncidentStatus, name="incident_status"), nullable=True
    )
    to_status: Mapped[IncidentStatus] = mapped_column(sa.Enum(IncidentStatus, name="incident_status"), nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="status_history")


class IncidentMessage(Base):
    __tablename__ = "incident_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sender_role: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="messages")


class IncidentResolutionNote(Base):
    __tablename__ = "incident_resolution_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    technician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="resolution_notes")


class IncidentEvaluation(Base):
    __tablename__ = "incident_evaluations"
    __table_args__ = (CheckConstraint("stars >= 1 AND stars <= 5", name="ck_incident_evaluations_stars_range"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id"), unique=True, nullable=False
    )
    noc_operator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    is_permanent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="evaluation")
