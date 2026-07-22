import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.schemas.contracts import FaultType


class TeamProfile(Base):
    """CP3: sadece tablo/model. identity.personnel.upserted event'inden senkronize edilen
    salt-okunur read-model cache'i - tuketici mantigi CP4'te eklenecek (bkz. ARCHITECTURE.md SS7)."""

    __tablename__ = "team_profile"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)  # = identity user_id
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    specializations: Mapped[list[FaultType]] = mapped_column(
        ARRAY(sa.Enum(FaultType, name="fault_type")), nullable=False, default=list
    )
    regions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    base_lat: Mapped[float] = mapped_column(Float, nullable=False)
    base_lon: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workload: Mapped["TeamWorkload | None"] = relationship(back_populates="team", uselist=False)


class TeamWorkload(Base):
    """CP3: sadece tablo/model. incident.assigned/status_changed/resolved event'lerinden
    senkronize edilen aktif is yuku sayaci - tuketici mantigi CP4'te eklenecek."""

    __tablename__ = "team_workload"

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("team_profile.id"), primary_key=True)
    active_incident_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    team: Mapped["TeamProfile"] = relationship(back_populates="workload")
