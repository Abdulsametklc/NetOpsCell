import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    action_type: str,
    result: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    detail: dict | None = None,
) -> None:
    """ARCHITECTURE.md §3.4: her kayıtta kim/ne/ne zaman/nereden/sonuç/detay bulunur
    (created_at kolonu server_default ile otomatik). Audit yazımı asıl işlemi
    engellememeli - çağıran taraf ayrı commit atar, burada sadece ekleyip flush ederiz."""
    db.add(
        AuditLog(
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            result=result,
            detail=detail,
        )
    )
    await db.commit()
