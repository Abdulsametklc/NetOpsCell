import asyncio
import time

import anthropic

from app.core.config import settings
from app.schemas.contracts import FaultType, TelemetryInput

# ARCHITECTURE.md SS8: LLM sadece iki fuzzy cikti uretir (probability, fault_type) + kisa
# gerekce. Esik/oncelik gibi kesin is kurallari LLM disinda, deterministik kodda uygulanir
# (bkz. thresholds.py).
SYSTEM_PROMPT = """Sen Turkcell sebeke altyapisinda uzman bir ariza teshis asistanisin.
Sana bir baz istasyonunun telemetri verisi verilecek (sinyal gucu, paket kaybi, sicaklik,
guc durumu, gecmis ariza sayisi). Gorevin bu verinin bir arizaya isaret edip etmedigini ve
ariza turunu belirlemek.

Kategoriler:
- DONANIM: fiziksel ekipman arizasi belirtileri (ozellikle tekrarlayan arizalar)
- GUC_KESINTISI: guc/batarya durumu anomalisi
- BAGLANTI: sinyal/paket kaybi kaynakli baglanti sorunu
- ISINMA: sicaklik anomalisi
- YAZILIM: davranissal/yazilimsal tutarsizlik belirtileri
- BELIRSIZ: veri yetersiz veya net degil (normal telemetri de buraya dahildir, dusuk olasilikla)

Ornekler:
- "sinyal stabil, sicaklik normal, paket kaybi yok" -> probability~0.05, BELIRSIZ (normal)
- "sicaklik hizla yukseliyor + paket kaybi artiyor" -> probability~0.9, ISINMA
- "guc kesintisi tespit edildi, batarya devrede, sinyal dusuk" -> probability~0.85, GUC_KESINTISI

emit_diagnosis tool'unu cagirarak yanit ver. Serbest metin yazma."""

DIAGNOSIS_TOOL = {
    "name": "emit_diagnosis",
    "description": "Baz istasyonu telemetri verisine dayanarak ariza olasiligi ve turunu bildirir.",
    "input_schema": {
        "type": "object",
        "properties": {
            "probability": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Ariza olasiligi (0.0 = kesinlikle normal, 1.0 = kesin ariza)",
            },
            "fault_type": {
                "type": "string",
                "enum": [ft.value for ft in FaultType],
            },
            "rationale": {"type": "string", "description": "Kisa gerekce (Turkce, 1-2 cumle)"},
        },
        "required": ["probability", "fault_type", "rationale"],
    },
}


def telemetry_to_text(payload: TelemetryInput) -> str:
    return (
        f"Istasyon {payload.station_code}: sinyal gucu {payload.signal_strength} dBm, "
        f"paket kaybi %{payload.packet_loss}, sicaklik {payload.temperature} C, "
        f"guc durumu: {payload.power_status.value}, "
        f"son 24 saatte gecmis ariza sayisi: {payload.recent_fault_count}."
    )


class LLMUnavailable(Exception):
    """LLM yapilandirilmamis, circuit breaker acik, ya da 1 retry sonrasi da basarisiz oldu.
    Cagiran taraf bu durumda rule_fallback'e dusmelidir."""


class CircuitBreaker:
    """Art arda N basarisizliktan sonra bir sure dogrudan fallback'e dusurup dis API'yi
    gereksiz yormamak icin basit bir devre kesici (bkz. ARCHITECTURE.md SS8.7)."""

    def __init__(self, failure_threshold: int, cooldown_seconds: float) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.cooldown_seconds:
            # sogutma penceresi gecti, tekrar denemeye izin ver (half-open)
            self._opened_at = None
            self._consecutive_failures = 0
            return False
        return True

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._opened_at = time.monotonic()


_breaker = CircuitBreaker(
    failure_threshold=settings.llm_circuit_breaker_threshold,
    cooldown_seconds=settings.llm_circuit_breaker_cooldown_seconds,
)

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None


async def diagnose(payload: TelemetryInput) -> tuple[float, FaultType, str]:
    if _client is None:
        raise LLMUnavailable("ANTHROPIC_API_KEY tanimli degil")
    if _breaker.is_open():
        raise LLMUnavailable("circuit breaker acik (son basarisizliklar sonrasi sogutma penceresinde)")

    last_error: Exception | None = None
    for attempt in range(2):  # ilk deneme + 1 retry
        try:
            response = await asyncio.wait_for(
                _client.messages.create(
                    model=settings.anthropic_model,
                    max_tokens=300,
                    temperature=0,
                    system=SYSTEM_PROMPT,
                    tools=[DIAGNOSIS_TOOL],
                    tool_choice={"type": "tool", "name": "emit_diagnosis"},
                    messages=[{"role": "user", "content": telemetry_to_text(payload)}],
                ),
                timeout=settings.llm_timeout_seconds,
            )
            tool_use = next((block for block in response.content if block.type == "tool_use"), None)
            if tool_use is None:
                raise LLMUnavailable("LLM bir tool_use blogu dondurmedi")

            data = tool_use.input
            _breaker.record_success()
            return float(data["probability"]), FaultType(data["fault_type"]), str(data.get("rationale", ""))
        except LLMUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - saglayici tarafli her hata fallback'e dusurmeli
            last_error = exc

    _breaker.record_failure()
    raise LLMUnavailable(str(last_error))
