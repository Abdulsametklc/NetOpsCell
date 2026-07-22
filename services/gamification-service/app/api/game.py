import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import PointLedger, UserStats

router = APIRouter(prefix="/api/v1/game", tags=["gamification"])


@router.get("/leaderboard")
async def leaderboard(period: str = "daily", limit: int = 10, db: AsyncSession = Depends(get_db)):
    """CP1 iskelet: donem filtresi (daily/weekly) CP4'te eklenecek, simdilik tum-zamanlar toplami."""
    result = await db.execute(
        select(PointLedger.user_id, func.sum(PointLedger.points).label("total"))
        .group_by(PointLedger.user_id)
        .order_by(func.sum(PointLedger.points).desc())
        .limit(limit)
    )
    rows = result.all()
    return {
        "success": True,
        "data": [{"user_id": str(user_id), "points": total} for user_id, total in rows],
        "error": None,
    }


@router.get("/profile/{user_id}")
async def profile(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stats = await db.get(UserStats, user_id)
    if stats is None:
        return {
            "success": True,
            "data": {
                "user_id": str(user_id),
                "total_points": 0,
                "level": "BRONZ",
                "resolved_count": 0,
                "avg_points": 0.0,
            },
            "error": None,
        }
    return {
        "success": True,
        "data": {
            "user_id": str(stats.user_id),
            "total_points": stats.total_points,
            "level": stats.level,
            "resolved_count": stats.resolved_count,
            "avg_points": stats.avg_points,
        },
        "error": None,
    }
