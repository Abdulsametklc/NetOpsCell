from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.geo import haversine_km
from app.models.team import TeamProfile, TeamWorkload
from app.schemas.contracts import FaultType

# ARCHITECTURE.md SS7: skor = (uzmanlik_eslesme x 0.4) + (mesafe_yakinlik x 0.3) + (bosluk_orani x 0.3)
EXPERTISE_WEIGHT = 0.4
DISTANCE_WEIGHT = 0.3
CAPACITY_WEIGHT = 0.3

# mesafe_yakinlik normalizasyon yaricapi (km) - bu yaricaptan uzak ekipler icin yakinlik 0'a gider.
DISTANCE_NORMALIZATION_KM = 50.0


class CandidateScore:
    def __init__(
        self,
        *,
        team_id: str,
        team_name: str,
        score: float,
        expertise: float,
        proximity: float,
        capacity_ratio: float,
        has_capacity: bool,
    ) -> None:
        self.team_id = team_id
        self.team_name = team_name
        self.score = score
        self.components = {
            "uzmanlik_eslesme": expertise,
            "mesafe_yakinlik": proximity,
            "bosluk_orani": capacity_ratio,
        }
        self.has_capacity = has_capacity

    def to_log_dict(self) -> dict:
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "score": self.score,
            "components": self.components,
        }


async def score_candidates(
    db: AsyncSession, *, fault_type: FaultType, lat: float, lng: float
) -> list[CandidateScore]:
    teams = (await db.execute(select(TeamProfile).where(TeamProfile.is_active.is_(True)))).scalars().all()

    candidates: list[CandidateScore] = []
    for team in teams:
        workload = await db.get(TeamWorkload, team.id)
        active_count = workload.active_incident_count if workload else 0

        expertise = 1.0 if fault_type in team.specializations else 0.0
        distance_km = haversine_km(lat, lng, team.base_lat, team.base_lon)
        proximity = max(0.0, 1.0 - distance_km / DISTANCE_NORMALIZATION_KM)
        capacity_ratio = max(0.0, 1.0 - (active_count / team.capacity)) if team.capacity > 0 else 0.0

        score = expertise * EXPERTISE_WEIGHT + proximity * DISTANCE_WEIGHT + capacity_ratio * CAPACITY_WEIGHT

        candidates.append(
            CandidateScore(
                team_id=str(team.id),
                team_name=team.name,
                score=score,
                expertise=expertise,
                proximity=proximity,
                capacity_ratio=capacity_ratio,
                has_capacity=active_count < team.capacity,
            )
        )

    return sorted(candidates, key=lambda c: c.score, reverse=True)


def pick_best(candidates: list[CandidateScore]) -> CandidateScore | None:
    feasible = [c for c in candidates if c.has_capacity]
    return feasible[0] if feasible else None
