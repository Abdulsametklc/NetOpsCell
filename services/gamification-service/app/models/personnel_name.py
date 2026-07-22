import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PersonnelName(Base):
    """identity.personnel.upserted event'inden senkronize edilen salt-okunur
    read-model cache'i (ai-service'in team_profile'i ile ayni desen) - liderlik
    tablosu ve profilde UUID yerine gercek isim gosterebilmek icin."""

    __tablename__ = "personnel_name"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
