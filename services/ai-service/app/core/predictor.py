from app.core.llm_client import LLMUnavailable, diagnose
from app.core.ml_fallback import ml_predict
from app.core.thresholds import derive_priority, derive_suggestion
from app.schemas.contracts import PredictionMethod, PredictResponse, TelemetryInput


async def predict(payload: TelemetryInput) -> PredictResponse:
    try:
        probability, fault_type, rationale = await diagnose(payload)
        method = PredictionMethod.LLM
        explanation = rationale
    except LLMUnavailable as exc:
        probability, fault_type = ml_predict(payload)
        method = PredictionMethod.ML_MODEL
        explanation = f"Egitilmis ML modeli fallback (LLM kullanilamadi: {exc})"

    return PredictResponse(
        probability=probability,
        fault_type=fault_type,
        priority=derive_priority(probability),
        suggestion=derive_suggestion(probability),
        method=method,
        confidence_explanation=explanation,
    )
