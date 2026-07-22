import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models import Badge, PersonnelName, PointLedger, UserBadge, UserStats

router = APIRouter(prefix="/api/v1/game", tags=["gamification"])


def _period_cutoff(period: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "daily":
        return today_start
    if period == "weekly":
        return today_start - timedelta(days=today_start.weekday())  # bu haftanin Pazartesisi
    return None


async def _names_for(db: AsyncSession, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not user_ids:
        return {}
    rows = await db.execute(select(PersonnelName).where(PersonnelName.user_id.in_(user_ids)))
    return {row.user_id: row.name for row in rows.scalars().all()}


@router.get("/leaderboard")
async def leaderboard(period: str = "daily", limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Case Bolum 6.4: gunluk/haftalik liderlik tablosu, ilk 10, puan sirali."""
    query = select(PointLedger.user_id, func.sum(PointLedger.points).label("total")).group_by(PointLedger.user_id)

    cutoff = _period_cutoff(period)
    if cutoff is not None:
        query = query.where(PointLedger.created_at >= cutoff)

    result = await db.execute(query.order_by(func.sum(PointLedger.points).desc()).limit(limit))
    rows = result.all()
    names = await _names_for(db, [user_id for user_id, _ in rows])
    return {
        "success": True,
        "data": [
            {"user_id": str(user_id), "points": total, "display_name": names.get(user_id)}
            for user_id, total in rows
        ],
        "error": None,
    }


async def _user_rank(db: AsyncSession, user_id: uuid.UUID) -> int | None:
    result = await db.execute(select(UserStats.user_id).order_by(UserStats.total_points.desc()))
    ordered_ids = [row[0] for row in result.all()]
    return ordered_ids.index(user_id) + 1 if user_id in ordered_ids else None


async def _user_badges(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    rows = (
        await db.execute(
            select(Badge.code, Badge.name, Badge.description, UserBadge.earned_at)
            .join(UserBadge, UserBadge.badge_id == Badge.id)
            .where(UserBadge.user_id == user_id)
            .order_by(UserBadge.earned_at)
        )
    ).all()
    return [
        {"code": code, "name": name, "description": description, "earned_at": earned_at.isoformat()}
        for code, name, description, earned_at in rows
    ]


@router.get("/profile/{user_id}")
async def profile(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ARCHITECTURE.md SS4.4: sadece self / SUPERVIZOR / ADMIN (IDOR korumasi)."""
    if current_user.user_id != user_id and current_user.role not in ("ADMIN", "SUPERVIZOR"):
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Başka bir kullanıcının profilini görüntüleyemezsiniz"},
        )

    badges = await _user_badges(db, user_id)
    name_cache = await db.get(PersonnelName, user_id)
    display_name = name_cache.name if name_cache else None

    stats = await db.get(UserStats, user_id)
    if stats is None:
        return {
            "success": True,
            "data": {
                "user_id": str(user_id),
                "display_name": display_name,
                "total_points": 0,
                "level": "BRONZ",
                "resolved_count": 0,
                "avg_points": 0.0,
                "rank": None,
                "badges": badges,
            },
            "error": None,
        }

    rank = await _user_rank(db, user_id)
    return {
        "success": True,
        "data": {
            "user_id": str(stats.user_id),
            "display_name": display_name,
            "total_points": stats.total_points,
            "level": stats.level,
            "resolved_count": stats.resolved_count,
            "avg_points": stats.avg_points,
            "rank": rank,
            "badges": badges,
        },
        "error": None,
    }
