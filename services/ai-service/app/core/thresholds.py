from app.schemas.contracts import Priority, Suggestion

# Case Bolum 5.1: "Olasilik 0.40 alti sadece izlenir, 0.85 uzeri acil vaka acilir. Aradakiler
# operator onayina duser." Bu esikler LLM/kural motorunun ciktisindan BAGIMSIZ, sabit iş
# kurallaridir - probability degeri hangi yontemden gelirse gelsin (LLM ya da fallback) ayni
# sekilde uygulanir. Boylece LLM'in olasi tutarsizligi (non-determinism) esik davranisina
# sizmaz (bkz. ARCHITECTURE.md SS8.1).
SUGGESTION_LOWER_THRESHOLD = 0.40
SUGGESTION_UPPER_THRESHOLD = 0.85


def derive_suggestion(probability: float) -> Suggestion:
    if probability < SUGGESTION_LOWER_THRESHOLD:
        return Suggestion.IZLE
    if probability <= SUGGESTION_UPPER_THRESHOLD:
        return Suggestion.VAKA_AC
    return Suggestion.ACIL


def derive_priority(probability: float) -> Priority:
    """NOT: case'teki "buyuk kapsama alani + yuksek olasilik -> KRITIK" kurali istasyon bazli
    bir kapsama/etkilenen-kullanici verisi gerektirir; bu veri mevcut TelemetryInput
    sozlesmesinde (docs/CONTRACTS.md) yok. Bilincli sadelestirme: oncelik sadece olasiliktan
    turetilir. Supervizor her zaman manuel degistirebilir (ARCHITECTURE.md SS4.3)."""
    if probability > SUGGESTION_UPPER_THRESHOLD:
        return Priority.KRITIK
    if probability > 0.7:
        return Priority.YUKSEK
    if probability > SUGGESTION_LOWER_THRESHOLD:
        return Priority.ORTA
    return Priority.DUSUK
