"""Kaynak: docs/CONTRACTS.md. Bu dosya elle senkronize edilir; CONTRACTS.md degisirse buraya da yansitilmali."""

from enum import Enum

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
