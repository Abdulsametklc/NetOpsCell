from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.predictor import predict
from app.models.prediction import Prediction
from app.schemas.contracts import TelemetryInput

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post("/predict")
async def predict_endpoint(payload: TelemetryInput, db: AsyncSession = Depends(get_db)):
    result = await predict(payload)

    record = Prediction(
        station_code=payload.station_code,
        input_features=payload.model_dump(mode="json"),
        probability=result.probability,
        fault_type=result.fault_type,
        priority=result.priority,
        suggestion=result.suggestion,
        method=result.method,
        confidence_explanation=result.confidence_explanation,
    )
    db.add(record)
    await db.commit()

    return {"success": True, "data": result.model_dump(), "error": None}
