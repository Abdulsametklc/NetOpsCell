from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.security import PUBLIC_KEY_PEM
from app.schemas.internal import InternalAuditRequest

# Bu router Gateway'in routing tablosuna dahil EDİLMEZ - sadece iç Docker ağından
# (netopscell-net) diğer servisler tarafından çağrılır (ARCHITECTURE.md §3.4).
router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/public-key")
async def get_public_key():
    """Gateway (CP3) RS256 imzasını bu public key ile doğrular - private key'e
    hiçbir zaman ihtiyaç duymaz (ARCHITECTURE.md §3.2)."""
    return {"public_key_pem": PUBLIC_KEY_PEM.decode()}


@router.post("/audit")
async def post_internal_audit(payload: InternalAuditRequest, db: AsyncSession = Depends(get_db)):
    """Diğer servisler (incident/ai/gamification) kendi 403'lerini buraya yazar
    (ARCHITECTURE.md §3.4 - 'basitlik için doğrudan Identity Service'in
    POST /internal/audit endpoint'i çağrılarak loglanır')."""
    await write_audit_log(
        db,
        user_id=payload.user_id,
        action_type=payload.action_type,
        result=payload.result,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        ip_address=payload.ip_address,
        detail=payload.detail,
    )
    return {"success": True, "data": None, "error": None}
