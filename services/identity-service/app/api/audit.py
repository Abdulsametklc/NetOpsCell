from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import require_roles
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["audit"])


@router.get("/audit-logs")
async def list_audit_logs(
    user_id: str | None = None,
    action_type: str | None = None,
    limit: int = 50,
    _: User = Depends(require_roles(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 200))
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action_type is not None:
        query = query.where(AuditLog.action_type == action_type)

    logs = (await db.execute(query)).scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action_type": log.action_type,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "result": log.result,
                "detail": log.detail,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "error": None,
    }
