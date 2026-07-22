from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import FIXED_OTP_CODE, create_access_token, hash_password
from app.models.otp_code import OtpCode
from app.models.user import User
from app.schemas.auth import (
    OtpVerifyRequest,
    PersonnelCreateRequest,
    RegisterCustomerRequest,
    RegisterCustomerResponse,
    TokenResponse,
    UserPublic,
)
from app.schemas.contracts import ResponseEnvelope

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register/customer", response_model=ResponseEnvelope[RegisterCustomerResponse])
async def register_customer(payload: RegisterCustomerRequest, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.gsm == payload.gsm))).scalar_one_or_none()

    if existing and existing.is_active:
        raise HTTPException(status_code=409, detail={"code": "ALREADY_REGISTERED", "message": "Bu GSM ile aktif bir hesap zaten var"})

    if existing:
        existing.first_name = payload.first_name
        existing.last_name = payload.last_name
        existing.email = payload.email
        user = existing
    else:
        user = User(
            role="MUSTERI",
            first_name=payload.first_name,
            last_name=payload.last_name,
            gsm=payload.gsm,
            email=payload.email,
            is_active=False,
        )
        db.add(user)

    now = datetime.now(timezone.utc)
    db.add(
        OtpCode(
            gsm=payload.gsm,
            code=FIXED_OTP_CODE,
            expires_at=now + timedelta(minutes=5),
        )
    )
    await db.commit()

    return ResponseEnvelope(success=True, data=RegisterCustomerResponse(gsm=payload.gsm))


@router.post("/otp/verify", response_model=ResponseEnvelope[TokenResponse])
async def verify_otp(payload: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.gsm == payload.gsm))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Bu GSM ile kayıtlı kullanıcı yok"})

    now = datetime.now(timezone.utc)
    otp = (
        await db.execute(
            select(OtpCode)
            .where(OtpCode.gsm == payload.gsm, OtpCode.verified_at.is_(None))
            .order_by(OtpCode.created_at.desc())
        )
    ).scalars().first()

    if not otp or otp.expires_at < now or otp.code != payload.code:
        raise HTTPException(status_code=422, detail={"code": "INVALID_OTP", "message": "OTP kodu geçersiz veya süresi dolmuş"})

    otp.verified_at = now
    user.is_active = True
    await db.commit()

    token = create_access_token(user)
    return ResponseEnvelope(
        success=True,
        data=TokenResponse(access_token=token, user=UserPublic(**user.__dict__)),
    )


@router.post("/personnel", response_model=ResponseEnvelope[UserPublic])
async def create_personnel(payload: PersonnelCreateRequest, db: AsyncSession = Depends(get_db)):
    # NOT: RBAC (Depends(require_roles(["ADMIN"]))) TASK_SPLIT.md CP4'te eklenecek.
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "ALREADY_REGISTERED", "message": "Bu e-posta ile bir hesap zaten var"})

    user = User(
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        specializations=payload.specializations,
        regions=payload.regions,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return ResponseEnvelope(success=True, data=UserPublic(**user.__dict__))
