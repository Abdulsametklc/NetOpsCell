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


class Suggestion(str, Enum):
    IZLE = "IZLE"
    VAKA_AC = "VAKA_AC"
    ACIL = "ACIL"


class IncidentStatus(str, Enum):
    YENI = "YENI"
    ATANDI = "ATANDI"
    YOLDA = "YOLDA"
    MUDAHALE_EDILIYOR = "MUDAHALE_EDILIYOR"
    PARCA_BEKLENIYOR = "PARCA_BEKLENIYOR"
    COZULDU = "COZULDU"
    KAPANDI = "KAPANDI"


class PowerStatus(str, Enum):
    NORMAL = "NORMAL"
    KESINTIDE = "KESINTIDE"


class PredictionMethod(str, Enum):
    LLM = "LLM"
    RULE_FALLBACK = "RULE_FALLBACK"


class TelemetryInput(BaseModel):
    station_code: str
    lat: float
    lng: float
    signal_strength: float
    packet_loss: float = Field(ge=0, le=100)
    temperature: float
    power_status: PowerStatus
    recent_fault_count: int = 0


class PredictResponse(BaseModel):
    probability: float = Field(ge=0.0, le=1.0)
    fault_type: FaultType
    priority: Priority
    suggestion: Suggestion
    method: PredictionMethod
    confidence_explanation: str


class ScoreComponents(BaseModel):
    uzmanlik_eslesme: float
    mesafe_yakinlik: float
    bosluk_orani: float


class AssignRequest(BaseModel):
    incident_id: str
    incident_number: str
    fault_type: FaultType
    priority: Priority
    lat: float
    lng: float


class AssignResponse(BaseModel):
    queued: bool
    team_id: str | None = None
    team_name: str | None = None
    score: float | None = None
    components: ScoreComponents | None = None


class IncidentAssigned(BaseModel):
    event_type: Literal["incident.assigned"] = "incident.assigned"
    incident_id: str
    team_id: str
    team_name: str
    score: float
    assigned_by: str
    assigned_at: datetime


class IncidentResolved(BaseModel):
    event_type: Literal["incident.resolved"] = "incident.resolved"
    incident_id: str
    team_id: str
    fault_type: FaultType
    priority: Priority
    created_at: datetime
    resolved_at: datetime
