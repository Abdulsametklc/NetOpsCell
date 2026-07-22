import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.assignment import pick_best, score_candidates
from app.core.database import get_db
from app.core.predictor import predict
from app.models.assignment_log import AssignmentLog
from app.models.prediction import Prediction
from app.schemas.contracts import AssignRequest, TelemetryInput

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


@router.post("/assign")
async def assign_endpoint(payload: AssignRequest, db: AsyncSession = Depends(get_db)):
    candidates = await score_candidates(db, fault_type=payload.fault_type, lat=payload.lat, lng=payload.lng)
    chosen = pick_best(candidates)

    log = AssignmentLog(
        incident_id=uuid.UUID(payload.incident_id),
        candidate_scores=[c.to_log_dict() for c in candidates],
        chosen_team_id=uuid.UUID(chosen.team_id) if chosen else None,
    )
    db.add(log)
    await db.commit()

    if chosen is None:
        return {
            "success": True,
            "data": {"queued": True, "team_id": None, "team_name": None, "score": None, "components": None},
            "error": None,
        }

    return {
        "success": True,
        "data": {
            "queued": False,
            "team_id": chosen.team_id,
            "team_name": chosen.team_name,
            "score": chosen.score,
            "components": chosen.components,
        },
        "error": None,
    }
