import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.schemas.contracts import FaultType, PredictionMethod, Priority, Suggestion


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    station_code: Mapped[str] = mapped_column(String(64), nullable=False)
    input_features: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    probability: Mapped[float] = mapped_column(Float, nullable=False)
    fault_type: Mapped[FaultType] = mapped_column(sa.Enum(FaultType, name="fault_type"), nullable=False)
    priority: Mapped[Priority] = mapped_column(sa.Enum(Priority, name="priority"), nullable=False)
    suggestion: Mapped[Suggestion] = mapped_column(sa.Enum(Suggestion, name="suggestion"), nullable=False)
    method: Mapped[PredictionMethod] = mapped_column(
        sa.Enum(PredictionMethod, name="prediction_method"), nullable=False
    )
    confidence_explanation: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
