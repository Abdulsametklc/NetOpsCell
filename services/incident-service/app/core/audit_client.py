import logging
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 2.0


async def report_unauthorized_access(
    *, user_id: uuid.UUID, role: str, resource_path: str, ip_address: str | None, required_roles: list[str]
) -> None:
    """Case §3.4: 'Yetkisiz erisim denemeleri (403)' audit log'a yazilmali. Identity Service
    tek audit tablosunu tuttugu icin (database-per-service) buraya dogrudan yazmak yerine
    kendi /internal/audit endpoint'i cagirilir (bkz. identity-service/app/api/internal.py)."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            await client.post(
                f"{settings.identity_service_url}/internal/audit",
                json={
                    "user_id": str(user_id),
                    "action_type": "UNAUTHORIZED_ACCESS",
                    "result": "FAILURE",
                    "resource_type": "endpoint",
                    "resource_id": resource_path,
                    "ip_address": ip_address,
                    "detail": {"required_roles": required_roles, "actual_role": role},
                },
            )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError):
        logger.exception("Audit log yazilamadi (identity-service'e ulasilamadi): %s", resource_path)
