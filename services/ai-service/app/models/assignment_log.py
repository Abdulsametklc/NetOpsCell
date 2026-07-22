import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssignmentLog(Base):
    """CP3: sadece tablo/model. POST /ai/assign (CP4) her cagrildiginda buraya adaylarin
    skorlarini ve secilen ekibi yazacak (seffaflik/demo icin, bkz. ARCHITECTURE.md SS7)."""

    __tablename__ = "assignment_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    candidate_scores: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    chosen_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
