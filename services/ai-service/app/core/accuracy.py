from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accuracy_feedback import AccuracyFeedback
from app.models.prediction import Prediction
from app.schemas.contracts import FaultType, Suggestion

# ARCHITECTURE.md SS8.8: NOC/Supervizor bir tahmini degistirmezse (KAPANDI'ya kadar hicbir
# incident.type_changed gelmezse) zimnen dogru sayilir. Pratik yaklasim: "toplam" = vaka acan
# tum tahminler (predictions.suggestion != IZLE), "yanlis" = accuracy_feedback'e dusen benzersiz
# incident sayisi. predictions ile accident arasinda incident_id FK'i olmadigi icin (iki tablo
# farkli aninlarda, birbirinden bagimsiz yazilir) satir-bazli join degil, agregat-seviyesinde
# kiyaslama yapilir - kategori toplamlari her iki tablonun kendi fault_type alanindan gelir.


async def compute_overall_accuracy(db: AsyncSession) -> dict:
    total = (
        await db.execute(select(func.count()).select_from(Prediction).where(Prediction.suggestion != Suggestion.IZLE))
    ).scalar_one()
    wrong = (
        await db.execute(select(func.count(func.distinct(AccuracyFeedback.incident_id))))
    ).scalar_one()

    accuracy_rate = round((total - wrong) / total * 100, 1) if total > 0 else None
    return {"total_evaluated": total, "incorrect_count": wrong, "accuracy_rate": accuracy_rate}


async def compute_accuracy_by_category(db: AsyncSession) -> dict:
    total_rows = await db.execute(
        select(Prediction.fault_type, func.count())
        .where(Prediction.suggestion != Suggestion.IZLE)
        .group_by(Prediction.fault_type)
    )
    total_by_category: dict[FaultType, int] = {row[0]: row[1] for row in total_rows.all()}

    wrong_rows = await db.execute(
        select(AccuracyFeedback.original_fault_type, func.count(func.distinct(AccuracyFeedback.incident_id))).group_by(
            AccuracyFeedback.original_fault_type
        )
    )
    wrong_by_category: dict[FaultType, int] = {row[0]: row[1] for row in wrong_rows.all()}

    breakdown = {}
    for fault_type, total in total_by_category.items():
        wrong = wrong_by_category.get(fault_type, 0)
        breakdown[fault_type.value] = {
            "total_evaluated": total,
            "incorrect_count": wrong,
            "accuracy_rate": round((total - wrong) / total * 100, 1) if total > 0 else None,
        }
    return breakdown
