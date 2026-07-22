from pathlib import Path

import joblib

from app.core.rule_fallback import rule_based_predict
from app.schemas.contracts import FaultType, PowerStatus, TelemetryInput

# LLM'e (veya LLM saglayicisina) ulasilamadiginda devreye giren birincil fallback:
# docs/sample_telemetry.json'daki 122 etiketli ornekle egitilmis bir
# RandomForestClassifier (bkz. app/ml/train_model.py, docs/ai-approach.md SS7).
# Model dosyasi bir sekilde eksik/bozuksa (ornegin repo model.joblib olmadan
# klonlandiysa) rule_based_predict'e (deterministik if/else) duser - ikinci
# bir savunma katmani, ana yol degil.
MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "model.joblib"

_bundle = None
if MODEL_PATH.exists():
    _bundle = joblib.load(MODEL_PATH)


def ml_predict(payload: TelemetryInput) -> tuple[float, FaultType]:
    """Egitilmis modelden (probability 0.0-1.0, en olasi ariza turu) dondurur.

    probability = P(BELIRSIZ degil), yani modelin bu telemetriyi gercek bir
    arizanin isareti olarak gorme olasiligi. fault_type, BELIRSIZ disindaki
    siniflar arasinda en yuksek olasilikli olandir.
    """
    if _bundle is None:
        return rule_based_predict(payload)

    pipeline = _bundle["pipeline"]
    features = [
        [
            payload.signal_strength,
            payload.packet_loss,
            payload.temperature,
            payload.recent_fault_count,
            1.0 if payload.power_status == PowerStatus.KESINTIDE else 0.0,
        ]
    ]
    proba = pipeline.predict_proba(features)[0]
    classes = pipeline.named_steps["clf"].classes_

    class_probs = dict(zip(classes, proba))
    p_belirsiz = class_probs.get(FaultType.BELIRSIZ.value, 0.0)
    probability = round(1.0 - p_belirsiz, 4)

    fault_candidates = {
        FaultType(k): v for k, v in class_probs.items() if k != FaultType.BELIRSIZ.value
    }
    fault_type = max(fault_candidates, key=fault_candidates.get) if fault_candidates else FaultType.BELIRSIZ

    return probability, fault_type
