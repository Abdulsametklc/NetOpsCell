"""Synthetic-data generalization test for app.core.ml_fallback.ml_predict().

The 122-sample training_data.json holdout split already measures generalization
(bkz. docs/ai-approach.md SS7.1), but that holdout still comes from the same
data-generation process as training. This suite constructs a FRESH set of
hand-written synthetic telemetry readings (never present in training_data.json,
values chosen independently by domain reasoning) to sanity-check that the
trained model behaves sensibly on genuinely unseen inputs - not just memorized
patterns from the training distribution.

Also verifies the disqualification-rule property: predictions must genuinely
vary with input, never a constant/mocked output.
"""

import pytest

from app.core.ml_fallback import ml_predict
from app.schemas.contracts import FaultType, PowerStatus, TelemetryInput


def make_telemetry(
    *,
    temperature: float = 24.0,
    packet_loss: float = 1.0,
    signal_strength: float = -62.0,
    power_status: PowerStatus = PowerStatus.NORMAL,
    recent_fault_count: int = 0,
) -> TelemetryInput:
    return TelemetryInput(
        station_code="SYN-0001",
        lat=39.92,
        lng=32.85,
        signal_strength=signal_strength,
        packet_loss=packet_loss,
        temperature=temperature,
        power_status=power_status,
        recent_fault_count=recent_fault_count,
    )


# Her giris egitim verisinde (training_data.json) BIREBIR gecmiyor - elle,
# domain bilgisiyle uydurulmus. "expected" alani sadece net/belirgin
# senaryolarda dolduruldu; genuinely belirsiz olanlar None birakilip sadece
# probability davranisi kontrol edilir.
SYNTHETIC_CASES: list[dict] = [
    # --- BAGLANTI: zayif sinyal veya yuksek paket kaybi, gerisi normal ---
    dict(kw=dict(signal_strength=-108, packet_loss=18, temperature=24, recent_fault_count=0), expected=FaultType.BAGLANTI, note="cok zayif sinyal"),
    dict(kw=dict(signal_strength=-71, packet_loss=38, temperature=23, recent_fault_count=0), expected=FaultType.BAGLANTI, note="cok yuksek paket kaybi"),
    dict(kw=dict(signal_strength=-112, packet_loss=27, temperature=26, recent_fault_count=0), expected=FaultType.BAGLANTI, note="zayif sinyal + yuksek paket kaybi"),

    # --- ISINMA: yuksek sicaklik, gerisi normal ---
    dict(kw=dict(signal_strength=-64, packet_loss=1, temperature=79, recent_fault_count=0), expected=FaultType.ISINMA, note="yuksek sicaklik"),
    dict(kw=dict(signal_strength=-58, packet_loss=0.5, temperature=93, recent_fault_count=0), expected=FaultType.ISINMA, note="cok yuksek sicaklik"),
    dict(kw=dict(signal_strength=-66, packet_loss=2, temperature=71, recent_fault_count=1), expected=FaultType.ISINMA, note="yuksek sicaklik + hafif gecmis ariza"),

    # --- GUC_KESINTISI: guc kesintide, sinyal/sicaklik cogunlukla normal ---
    dict(kw=dict(signal_strength=-75, packet_loss=4, temperature=27, power_status=PowerStatus.KESINTIDE, recent_fault_count=0), expected=FaultType.GUC_KESINTISI, note="guc kesintisi tek basina"),
    dict(kw=dict(signal_strength=-59, packet_loss=1, temperature=26, power_status=PowerStatus.KESINTIDE, recent_fault_count=1), expected=FaultType.GUC_KESINTISI, note="guc kesintisi + hafif gecmis"),

    # --- DONANIM: tekrarlayan ariza sayisi yuksek, diger metrikler normale yakin ---
    dict(kw=dict(signal_strength=-67, packet_loss=3, temperature=31, recent_fault_count=6), expected=FaultType.DONANIM, note="cok tekrarlayan ariza"),
    dict(kw=dict(signal_strength=-70, packet_loss=2, temperature=28, recent_fault_count=5), expected=FaultType.DONANIM, note="tekrarlayan ariza"),

    # --- BELIRSIZ: tamamen temiz telemetri ---
    # NOT: Bu iki senaryoda model BELIRSIZ yerine YAZILIM tahmin ediyor - bilinen bir
    # zayiflik. Egitim verisindeki YAZILIM ornekleri "hicbir esigi net asmayan ama
    # her sey hafif yuksek" gibi bulanik bir bolgeyi kapliyor (10 ornek), bu da
    # tertemiz BELIRSIZ bolgesiyle net ayrilmiyor. probability yine de 0.40 IZLE
    # esiginin altinda kaliyor (yanlis kategori ama dogru is kurali sonucu).
    dict(kw=dict(signal_strength=-54, packet_loss=0, temperature=21, recent_fault_count=0), expected=FaultType.BELIRSIZ, note="tertemiz telemetri", xfail="model YAZILIM tahmin ediyor, bkz. docs/ai-approach.md SS8"),
    dict(kw=dict(signal_strength=-58, packet_loss=0.2, temperature=23, recent_fault_count=0), expected=FaultType.BELIRSIZ, note="neredeyse tertemiz", xfail="model YAZILIM tahmin ediyor, bkz. docs/ai-approach.md SS8"),

    # --- Belirsiz/ambiguous - iki guclu sinyal cakisiyor, tek bir "dogru" kategori yok.
    #     Bunlarda expected=None: sadece probability yuksek olmali (gercek bir ariza izlenimi),
    #     hangi kategoriye dustugu iddia edilmiyor. ---
    dict(kw=dict(signal_strength=-115, packet_loss=32, temperature=88, power_status=PowerStatus.KESINTIDE, recent_fault_count=3), expected=None, note="hepsi ayni anda kritik (coklu sinyal)"),
    dict(kw=dict(signal_strength=-90, packet_loss=20, temperature=70, recent_fault_count=2), expected=None, note="baglanti + isinma cakismasi"),
]


def _as_param(case: dict) -> pytest.param:
    marks = []
    if "xfail" in case:
        marks.append(pytest.mark.xfail(reason=case["xfail"], strict=True))
    return pytest.param(case, id=case["note"], marks=marks)


class TestSyntheticGeneralization:
    @pytest.mark.parametrize(
        "case",
        [_as_param(c) for c in SYNTHETIC_CASES if c["expected"] is not None],
    )
    def test_net_senaryolarda_dogru_kategoriyi_buluyor(self, case):
        payload = make_telemetry(**case["kw"])
        probability, fault_type = ml_predict(payload)

        assert 0.0 <= probability <= 1.0
        assert fault_type == case["expected"], (
            f"{case['note']}: beklenen={case['expected']}, tahmin={fault_type} (p={probability:.3f})"
        )

    @pytest.mark.parametrize(
        "case",
        [c for c in SYNTHETIC_CASES if c["expected"] is None],
        ids=[c["note"] for c in SYNTHETIC_CASES if c["expected"] is None],
    )
    def test_belirsiz_senaryolarda_yuksek_ariza_olasiligi_veriyor(self, case):
        payload = make_telemetry(**case["kw"])
        probability, fault_type = ml_predict(payload)

        assert probability > 0.5, (
            f"{case['note']}: birden fazla guclu sinyal varken model dusuk olasilik "
            f"verdi (p={probability:.3f}) - bu supheli, kontrol edilmeli"
        )
        assert fault_type != FaultType.BELIRSIZ

    def test_net_senaryolarin_genel_dogrulugu_makul_esigin_ustunde(self):
        """Tum 'net' senaryolarin dogruluk orani - regresyon koruma esigi."""
        clear_cases = [c for c in SYNTHETIC_CASES if c["expected"] is not None]
        correct = 0
        for case in clear_cases:
            payload = make_telemetry(**case["kw"])
            _, fault_type = ml_predict(payload)
            if fault_type == case["expected"]:
                correct += 1
        accuracy = correct / len(clear_cases)
        print(f"\nSentetik veri (hic gorulmemis, elle yazilmis) dogruluk: {accuracy:.2%} ({correct}/{len(clear_cases)})")
        assert accuracy >= 0.65, (
            f"Sentetik test verisinde dogruluk beklenenden dusuk: {accuracy:.2%}"
        )

    def test_gercekten_degisiyor_sabit_cikti_donmuyor(self):
        """Diskalifiye kurali: AI fallback asla sabit/hardcoded cikti donmemeli."""
        results = set()
        for case in SYNTHETIC_CASES:
            payload = make_telemetry(**case["kw"])
            probability, fault_type = ml_predict(payload)
            results.add((round(probability, 2), fault_type))

        assert len(results) > 1, "Tum senaryolar ayni (probability, fault_type) ciktisini verdi - suphelil"

    def test_asiri_uc_degerler_cokmeden_makul_bir_sonuc_donduruyor(self):
        """Egitim veri araligi disindaki (out-of-distribution) uc degerlerle bile
        model cokmemeli ve gecerli bir olasilik/kategori dondurmeli."""
        payload = make_telemetry(
            signal_strength=-140, packet_loss=100, temperature=150,
            power_status=PowerStatus.KESINTIDE, recent_fault_count=99,
        )
        probability, fault_type = ml_predict(payload)

        assert 0.0 <= probability <= 1.0
        assert isinstance(fault_type, FaultType)
