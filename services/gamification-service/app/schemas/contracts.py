"""Kaynak: docs/CONTRACTS.md. Bu dosya elle senkronize edilir; CONTRACTS.md degisirse buraya da yansitilmali."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class FaultType(str, Enum):
    DONANIM = "DONANIM"
    GUC_KESINTISI = "GUC_KESINTISI"
    BAGLANTI = "BAGLANTI"
    YAZILIM = "YAZILIM"
    ISINMA = "ISINMA"
    BELIRSIZ = "BELIRSIZ"


class Priority(str, Enum):
    DUSUK = "DUSUK"
    ORTA = "ORTA"
    YUKSEK = "YUKSEK"
    KRITIK = "KRITIK"


class Level(str, Enum):
    BRONZ = "BRONZ"
    GUMUS = "GUMUS"
    ALTIN = "ALTIN"
    PLATIN = "PLATIN"


class IncidentResolved(BaseModel):
    event_type: Literal["incident.resolved"] = "incident.resolved"
    incident_id: str
    team_id: str
    fault_type: FaultType
    priority: Priority
    created_at: datetime
    resolved_at: datetime


class IncidentEvaluated(BaseModel):
    event_type: Literal["incident.evaluated"] = "incident.evaluated"
    incident_id: str
    stars: int = Field(ge=1, le=5)
    is_permanent: bool
    evaluated_by: str


class IncidentSlaBreached(BaseModel):
    event_type: Literal["incident.sla_breached"] = "incident.sla_breached"
    incident_id: str
    priority: Priority
    sla_due_at: datetime
    breached_at: datetime


class IncidentCreated(BaseModel):
    event_type: Literal["incident.created"] = "incident.created"
    incident_id: str
    incident_number: str
    station_code: str
    fault_type: FaultType
    priority: Priority
    probability: float
    created_at: datetime


class GamePointsAwarded(BaseModel):
    event_type: Literal["game.points_awarded"] = "game.points_awarded"
    user_id: str
    incident_id: str | None
    points: int
    reason: str
    new_total: int


class BadgeEarned(BaseModel):
    event_type: Literal["badge.earned"] = "badge.earned"
    user_id: str
    badge_code: str
    earned_at: datetime
