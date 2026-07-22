import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.event_publisher import publish_event
from app.core.rbac import require_roles
from app.core.serializers import user_to_public
from app.models.user import User
from app.schemas.auth import UserPublic, UserUpdateRequest
from app.schemas.contracts import ResponseEnvelope
from app.schemas.events import IdentityPersonnelUpserted

router = APIRouter(prefix="/api/v1/auth", tags=["users"])


@router.get("/users", response_model=ResponseEnvelope[list[UserPublic]])
async def list_users(
    role: str | None = None,
    is_active: bool | None = None,
    current_user: User = Depends(require_roles(["ADMIN", "SUPERVIZOR"])),
    db: AsyncSession = Depends(get_db),
):
    query = select(User).where(User.role != "MUSTERI")
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    users = (await db.execute(query.order_by(User.created_at.desc()))).scalars().all()
    return ResponseEnvelope(success=True, data=[user_to_public(u) for u in users])


@router.patch("/users/{user_id}", response_model=ResponseEnvelope[UserPublic])
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Kullanıcı bulunamadı"})

    original_role = user.role
    if payload.role is not None:
        user.role = payload.role
    if payload.specializations is not None:
        user.specializations = payload.specializations
    if payload.regions is not None:
        user.regions = payload.regions
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.base_lat is not None:
        user.base_lat = payload.base_lat
    if payload.base_lon is not None:
        user.base_lon = payload.base_lon

    await db.commit()
    await db.refresh(user)

    if payload.role is not None and payload.role != original_role:
        await write_audit_log(
            db,
            user_id=current_user.id,
            action_type="ROLE_CHANGED",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=request.client.host if request.client else None,
            result="SUCCESS",
            detail={"from_role": original_role, "to_role": user.role},
        )

    if user.role == "SAHA_TEKNISYENI" and user.base_lat is not None and user.base_lon is not None:
        await publish_event(
            "identity.personnel.upserted",
            IdentityPersonnelUpserted(
                user_id=str(user.id),
                name=f"{user.first_name} {user.last_name}",
                specializations=user.specializations or [],
                regions=user.regions or [],
                base_lat=user.base_lat,
                base_lon=user.base_lon,
                is_active=user.is_active,
            ),
        )

    return ResponseEnvelope(success=True, data=user_to_public(user))
