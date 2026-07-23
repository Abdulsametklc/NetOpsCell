import uuid

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.audit_client import report_unauthorized_access


class CurrentUser:
    def __init__(self, user_id: uuid.UUID, role: str) -> None:
        self.user_id = user_id
        self.role = role


async def get_current_user(
    x_user_id: uuid.UUID | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> CurrentUser:
    """Gateway, JWT dogruladiktan sonra bu header'lari ekler (bkz. ARCHITECTURE.md SS5 - Gateway
    JWT'yi cozup X-User-Id/X-User-Role/... header'lari olarak downstream'e iletir). Gateway henuz
    insa edilmedigi icin dogrudan test ederken bu header'lari elle gondermeniz gerekir."""
    if x_user_id is None or x_user_role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHENTICATED",
                "message": "X-User-Id ve X-User-Role header'lari gerekli",
            },
        )
    return CurrentUser(user_id=x_user_id, role=x_user_role)


def require_roles(allowed_roles: list[str]):
    """identity-service/app/core/rbac.py ile ayni desen: Depends(require_roles([...])).
    Yetkisiz erisim denemesi 403 doner ve identity-service'in audit log'una
    UNAUTHORIZED_ACCESS olarak yazilir (case S3.4 - jüri "musteri token'iyla süpervizör
    endpoint'i cagirma" senaryosunu dener)."""

    async def dependency(
        request: Request,
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role not in allowed_roles:
            await report_unauthorized_access(
                user_id=current_user.user_id,
                role=current_user.role,
                resource_path=request.url.path,
                ip_address=request.client.host if request.client else None,
                required_roles=allowed_roles,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": f"'{current_user.role}' rolü bu işlemi yapamaz"},
            )
        return current_user

    return dependency
