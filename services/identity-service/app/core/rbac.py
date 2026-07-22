from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User


def require_roles(allowed_roles: list[str]):
    """TASK_SPLIT.md §4 (CP4): Depends(require_roles([...])) deseni. Yetkisiz erişim
    denemesi 403 döner ve audit log'a UNAUTHORIZED_ACCESS olarak yazılır
    (ARCHITECTURE.md §3.1/§3.4)."""

    async def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.role not in allowed_roles:
            await write_audit_log(
                db,
                user_id=current_user.id,
                action_type="UNAUTHORIZED_ACCESS",
                resource_type="endpoint",
                resource_id=request.url.path,
                ip_address=request.client.host if request.client else None,
                result="FAILURE",
                detail={"required_roles": allowed_roles, "actual_role": current_user.role},
            )
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": f"'{current_user.role}' rolü bu işlemi yapamaz"},
            )
        return current_user

    return dependency
