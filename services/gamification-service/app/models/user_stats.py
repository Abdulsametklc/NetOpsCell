import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, Float, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.schemas.contracts import Level


class UserStats(Base):
    __tablename__ = "user_stats"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[Level] = mapped_column(sa.Enum(Level, name="user_level"), nullable=False, default=Level.BRONZ)
    resolved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_points: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
