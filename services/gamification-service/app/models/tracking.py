import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.schemas.contracts import FaultType


class StationResolutionLog(Base):
    """CP5: her istasyon icin en son cozumu kimin yaptigini tutar - tekrar eden ariza
    tespiti (24 saat penceresi) icin gerekli (bkz. consumers/handlers.py, case Bolum 6.1)."""

    __tablename__ = "station_resolution_log"

    station_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FaultTypeResolutionCount(Base):
    """CP5: kullanici basina, ariza turune gore cozum sayaci - "Uzman" rozeti
    (tek turde 50 cozum) icin gerekli."""

    __tablename__ = "fault_type_resolution_counts"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    fault_type: Mapped[FaultType] = mapped_column(
        sa.Enum(FaultType, name="fault_type"), primary_key=True
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
