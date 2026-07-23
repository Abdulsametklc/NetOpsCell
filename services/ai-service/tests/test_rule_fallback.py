"""Unit tests for app.core.rule_fallback.rule_based_predict().

The single most important property tested here is that the rule engine is NOT
a constant/mocked output generator: different telemetry inputs must produce
genuinely different (probability, fault_type) results. A hackathon
disqualification rule states the AI service can never return a hardcoded
value, so this suite explicitly asserts that varying one signal at a time
changes the outcome.
"""

import pytest

from app.core.rule_fallback import (
    PACKET_LOSS_THRESHOLD_PCT,
    PACKET_LOSS_WEIGHT,
    POWER_OUTAGE_WEIGHT,
    RECURRING_FAULT_THRESHOLD_COUNT,
    RECURRING_FAULT_WEIGHT,
    SIGNAL_STRENGTH_THRESHOLD_DBM,
    SIGNAL_STRENGTH_WEIGHT,
    TEMPERATURE_THRESHOLD_C,
    TEMPERATURE_WEIGHT,
    rule_based_predict,
)
from app.schemas.contracts import FaultType, PowerStatus, TelemetryInput


def make_telemetry(
    *,
    temperature: float = 25.0,
    packet_loss: float = 0.0,
    signal_strength: float = -60.0,
    power_status: PowerStatus = PowerStatus.NORMAL,
    recent_fault_count: int = 0,
) -> TelemetryInput:
    """Builds a baseline-normal telemetry reading, overriding only what's needed."""
    return TelemetryInput(
        station_code="IST-0001",
        lat=41.0082,
        lng=28.9784,
        signal_strength=signal_strength,
        packet_loss=packet_loss,
        temperature=temperature,
        power_status=power_status,
        recent_fault_count=recent_fault_count,
    )


class TestFullyNormalTelemetry:
    def test_hicbir_esik_asilmazsa_probability_sifir_ve_belirsiz(self):
        payload = make_telemetry()

        probability, fault_type = rule_based_predict(payload)

        assert probability == 0.0
        assert fault_type == FaultType.BELIRSIZ


class TestIndividualThresholdContributions:
    def test_yuksek_sicaklik_isinma_katkisi_yapar(self):
        payload = make_telemetry(temperature=70.0)

        probability, fault_type = rule_based_predict(payload)

        assert probability == pytest.approx(TEMPERATURE_WEIGHT)
        assert fault_type == FaultType.ISINMA

    def test_yuksek_packet_loss_baglanti_katkisi_yapar(self):
        payload = make_telemetry(packet_loss=20.0)

        probability, fault_type = rule_based_predict(payload)

        assert probability == pytest.approx(PACKET_LOSS_WEIGHT)
        assert fault_type == FaultType.BAGLANTI

    def test_zayif_sinyal_baglanti_katkisi_yapar(self):
        payload = make_telemetry(signal_strength=-110.0)

        probability, fault_type = rule_based_predict(payload)

        assert probability == pytest.approx(SIGNAL_STRENGTH_WEIGHT)
        assert fault_type == FaultType.BAGLANTI

    def test_guc_kesintisi_guc_kesintisi_katkisi_yapar(self):
        payload = make_telemetry(power_status=PowerStatus.KESINTIDE)

        probability, fault_type = rule_based_predict(payload)

        assert probability == pytest.approx(POWER_OUTAGE_WEIGHT)
        assert fault_type == FaultType.GUC_KESINTISI

    def test_tekrarlayan_ariza_donanim_katkisi_yapar(self):
        payload = make_telemetry(recent_fault_count=RECURRING_FAULT_THRESHOLD_COUNT)

        probability, fault_type = rule_based_predict(payload)

        assert probability == pytest.approx(RECURRING_FAULT_WEIGHT)
        assert fault_type == FaultType.DONANIM


class TestThresholdBoundaries:
    """Thresholds are strict '>' (or '>=' for recent_fault_count) - value exactly at the
    threshold must NOT trigger a contribution."""

    def test_sicaklik_tam_esikte_tetiklenmez(self):
        payload = make_telemetry(temperature=TEMPERATURE_THRESHOLD_C)

        probability, fault_type = rule_based_predict(payload)

        assert probability == 0.0
        assert fault_type == FaultType.BELIRSIZ

    def test_packet_loss_tam_esikte_tetiklenmez(self):
        payload = make_telemetry(packet_loss=PACKET_LOSS_THRESHOLD_PCT)

        probability, fault_type = rule_based_predict(payload)

        assert probability == 0.0
        assert fault_type == FaultType.BELIRSIZ

    def test_sinyal_tam_esikte_tetiklenmez(self):
        payload = make_telemetry(signal_strength=SIGNAL_STRENGTH_THRESHOLD_DBM)

        probability, fault_type = rule_based_predict(payload)

        assert probability == 0.0
        assert fault_type == FaultType.BELIRSIZ

    def test_tekrarlayan_ariza_esik_altinda_tetiklenmez(self):
        payload = make_telemetry(recent_fault_count=RECURRING_FAULT_THRESHOLD_COUNT - 1)

        probability, fault_type = rule_based_predict(payload)

        assert probability == 0.0
        assert fault_type == FaultType.BELIRSIZ


class TestCombinedContributionsAndCap:
    def test_birden_fazla_esik_asimi_olasiliklari_toplar(self):
        payload = make_telemetry(temperature=70.0, packet_loss=20.0)

        probability, fault_type = rule_based_predict(payload)

        assert probability == pytest.approx(TEMPERATURE_WEIGHT + PACKET_LOSS_WEIGHT)
        # ISINMA (0.35) tek basina BAGLANTI'nin (0.30) katkisindan buyuk -> baskin tur ISINMA.
        assert fault_type == FaultType.ISINMA

    def test_esit_agirlikta_birden_fazla_katki_ilk_eklenen_turu_secer(self):
        """temperature (ISINMA, 0.35) ve power_status (GUC_KESINTISI, 0.35) esit agirlikta;
        fonksiyon icindeki kontrol sirasina gore ISINMA once eklendigi icin baskin olmali."""
        payload = make_telemetry(temperature=70.0, power_status=PowerStatus.KESINTIDE)

        probability, fault_type = rule_based_predict(payload)

        assert probability == pytest.approx(TEMPERATURE_WEIGHT + POWER_OUTAGE_WEIGHT)
        assert fault_type == FaultType.ISINMA

    def test_tum_esikler_asilinca_olasilik_099da_sinirlanir(self):
        payload = make_telemetry(
            temperature=100.0,
            packet_loss=100.0,
            signal_strength=-150.0,
            power_status=PowerStatus.KESINTIDE,
            recent_fault_count=10,
        )

        probability, fault_type = rule_based_predict(payload)

        raw_sum = (
            TEMPERATURE_WEIGHT
            + PACKET_LOSS_WEIGHT
            + SIGNAL_STRENGTH_WEIGHT
            + POWER_OUTAGE_WEIGHT
            + RECURRING_FAULT_WEIGHT
        )
        assert raw_sum > 0.99  # guard: the scenario must actually exceed the cap
        assert probability == 0.99
        # BAGLANTI gets both PACKET_LOSS_WEIGHT (0.30) and SIGNAL_STRENGTH_WEIGHT (0.20) =
        # 0.50, higher than any single other fault_type's contribution (ISINMA/GUC_KESINTISI
        # at 0.35, DONANIM at 0.15) - so BAGLANTI is genuinely the dominant contributor here.
        assert fault_type == FaultType.BAGLANTI

    @pytest.mark.parametrize(
        "temperature, packet_loss, signal_strength, power_status, recent_fault_count",
        [
            (25.0, 0.0, -60.0, PowerStatus.NORMAL, 0),
            (70.0, 0.0, -60.0, PowerStatus.NORMAL, 0),
            (25.0, 20.0, -60.0, PowerStatus.NORMAL, 0),
            (25.0, 0.0, -60.0, PowerStatus.KESINTIDE, 0),
            (25.0, 0.0, -60.0, PowerStatus.NORMAL, 3),
        ],
    )
    def test_olasilik_daima_0_ile_099_araliginda(
        self, temperature, packet_loss, signal_strength, power_status, recent_fault_count
    ):
        payload = make_telemetry(
            temperature=temperature,
            packet_loss=packet_loss,
            signal_strength=signal_strength,
            power_status=power_status,
            recent_fault_count=recent_fault_count,
        )

        probability, _ = rule_based_predict(payload)

        assert 0.0 <= probability <= 0.99


class TestOutputVariesWithInput:
    """Explicit non-determinism-by-design check: the case's disqualification rule says the
    AI service must never return a hardcoded/constant output. These assertions prove distinct
    inputs genuinely yield distinct outputs from the pure rule engine."""

    def test_farkli_girdiler_farkli_ciktilar_uretir(self):
        normal = make_telemetry()
        overheating = make_telemetry(temperature=90.0)
        connectivity = make_telemetry(packet_loss=50.0)
        power_outage = make_telemetry(power_status=PowerStatus.KESINTIDE)
        hardware = make_telemetry(recent_fault_count=5)

        results = [
            rule_based_predict(normal),
            rule_based_predict(overheating),
            rule_based_predict(connectivity),
            rule_based_predict(power_outage),
            rule_based_predict(hardware),
        ]

        # No two distinct-condition scenarios should collapse to the exact same (prob, type).
        assert len(set(results)) == len(results)

    def test_ayni_girdi_ayni_cikti_deterministik(self):
        payload = make_telemetry(temperature=80.0, recent_fault_count=4)

        first = rule_based_predict(payload)
        second = rule_based_predict(payload)

        assert first == second
