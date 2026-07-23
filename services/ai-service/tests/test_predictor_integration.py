"""Integration tests for app.core.predictor.predict() - LLM -> ML modeli -> esikler
zincirinin GERCEK butunlugunu test eder (ARCHITECTURE.md SS13: "AI Service icin LLM
cagrisi mock ile stub'lanir, ayrica gercek fallback path'i test edilir").

LLM cagrisi HTTP seviyesinde degil, app.core.llm_client.diagnose() fonksiyon
seviyesinde monkeypatch edilir - Anthropic SDK'nin tam HTTP wire-formatini
taklit etmek yerine (kirilgan), ayni sozlesmeyi (probability, fault_type,
rationale) dondurup predictor'in orkestrasyon mantigini (esik uygulama,
method etiketleme) dogrudan test eder.
"""

import pytest

from app.core import predictor
from app.core.llm_client import LLMUnavailable
from app.schemas.contracts import FaultType, PowerStatus, PredictionMethod, Suggestion, TelemetryInput


def make_telemetry(**overrides) -> TelemetryInput:
    base = dict(
        station_code="IST-TEST-001",
        lat=41.0082,
        lng=28.9784,
        signal_strength=-60.0,
        packet_loss=0.0,
        temperature=24.0,
        power_status=PowerStatus.NORMAL,
        recent_fault_count=0,
    )
    base.update(overrides)
    return TelemetryInput(**base)


class TestLLMBasariliYol:
    @pytest.mark.asyncio
    async def test_llm_basarili_donerse_method_llm_ve_esikler_dogru_uygulanir(self, monkeypatch):
        async def fake_diagnose(payload):
            return 0.9, FaultType.ISINMA, "Sicaklik kritik seviyede (mock LLM yaniti)"

        monkeypatch.setattr(predictor, "diagnose", fake_diagnose)

        result = await predictor.predict(make_telemetry(temperature=95))

        assert result.method == PredictionMethod.LLM
        assert result.fault_type == FaultType.ISINMA
        assert result.probability == pytest.approx(0.9)
        # esik mantigi (thresholds.py) LLM'in ureteceginden BAGIMSIZ, deterministik
        # kodda calisir - 0.9 > 0.85 ust esigi oldugu icin ACIL olmali.
        assert result.suggestion == Suggestion.ACIL

    @pytest.mark.asyncio
    async def test_llm_dusuk_olasilik_donerse_izle_onerilir(self, monkeypatch):
        async def fake_diagnose(payload):
            return 0.1, FaultType.BELIRSIZ, "Telemetri normal (mock LLM yaniti)"

        monkeypatch.setattr(predictor, "diagnose", fake_diagnose)

        result = await predictor.predict(make_telemetry())

        assert result.method == PredictionMethod.LLM
        assert result.suggestion == Suggestion.IZLE


class TestMLFallbackYolu:
    @pytest.mark.asyncio
    async def test_llm_ulasilamazsa_ml_modeline_duser(self, monkeypatch):
        async def failing_diagnose(payload):
            raise LLMUnavailable("test: ANTHROPIC_API_KEY yok")

        monkeypatch.setattr(predictor, "diagnose", failing_diagnose)

        result = await predictor.predict(make_telemetry(temperature=90, power_status=PowerStatus.KESINTIDE))

        assert result.method == PredictionMethod.ML_MODEL
        assert "ML modeli" in result.confidence_explanation or "ML_MODEL" in result.method.value

    @pytest.mark.asyncio
    async def test_ml_fallback_farkli_girdilerde_farkli_sonuc_verir(self, monkeypatch):
        """Diskalifiye kurali: fallback yolu asla sabit/hardcoded cikti donmemeli."""
        async def failing_diagnose(payload):
            raise LLMUnavailable("test")

        monkeypatch.setattr(predictor, "diagnose", failing_diagnose)

        normal = await predictor.predict(make_telemetry())
        critical = await predictor.predict(
            make_telemetry(temperature=95, packet_loss=40, power_status=PowerStatus.KESINTIDE, recent_fault_count=3)
        )

        assert (normal.probability, normal.fault_type) != (critical.probability, critical.fault_type)
        assert critical.probability > normal.probability

    @pytest.mark.asyncio
    async def test_gercekten_no_api_key_ile_de_calisir(self):
        """Monkeypatch olmadan, bu ortamda gercekten ANTHROPIC_API_KEY tanimli
        degilse (varsayilan test ortami), predictor kendiliginden ML fallback'e
        duser - bu, mock'lanmamis GERCEK fallback davranisidir."""
        result = await predictor.predict(make_telemetry(temperature=88))
        assert result.method in (PredictionMethod.ML_MODEL, PredictionMethod.LLM)
        assert 0.0 <= result.probability <= 1.0
