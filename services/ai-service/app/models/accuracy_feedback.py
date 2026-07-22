import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.schemas.contracts import FaultType


class AccuracyFeedback(Base):
    """CP3: sadece tablo/model. NOC/Supervizor bir tahmini degistirdiginde (incident.type_changed
    event'i) buraya kayit dusme mantigi CP4/CP6'da eklenecek (bkz. TASK_SPLIT.md)."""

    __tablename__ = "accuracy_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    original_fault_type: Mapped[FaultType] = mapped_column(sa.Enum(FaultType, name="fault_type"), nullable=False)
    corrected_fault_type: Mapped[FaultType | None] = mapped_column(
        sa.Enum(FaultType, name="fault_type"), nullable=True
    )
    corrected_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    corrected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
