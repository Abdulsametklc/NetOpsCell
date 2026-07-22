from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.event_publisher import publish_event
from app.core.rbac import require_roles
from app.core.serializers import user_to_public
from app.core.security import (
    FIXED_OTP_CODE,
    LOCKOUT_MINUTES,
    LOCKOUT_THRESHOLD,
    REFRESH_TOKEN_DAYS,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.models.otp_code import OtpCode
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.events import IdentityPersonnelUpserted
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    OtpVerifyRequest,
    PersonnelCreateRequest,
    RefreshRequest,
    RegisterCustomerRequest,
    RegisterCustomerResponse,
    TokenPair,
    TokenResponse,
    UserPublic,
)
from app.schemas.contracts import ResponseEnvelope

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def _issue_token_pair(db: AsyncSession, user: User) -> tuple[str, str]:
    access_token = create_access_token(user)
    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS),
        )
    )
    await db.commit()
    return access_token, raw_refresh


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

    access_token, refresh_token = await _issue_token_pair(db, user)
    return ResponseEnvelope(
        success=True,
        data=TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_to_public(user)),
    )


@router.post("/personnel", response_model=ResponseEnvelope[UserPublic])
async def create_personnel(
    payload: PersonnelCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_roles(["ADMIN"])),
):
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "ALREADY_REGISTERED", "message": "Bu e-posta ile bir hesap zaten var"})

    violations = validate_password_strength(payload.password)
    if violations:
        raise HTTPException(
            status_code=422,
            detail={"code": "WEAK_PASSWORD", "message": "Şifre politikaya uymuyor", "violations": violations},
        )

    if payload.role == "SAHA_TEKNISYENI" and (payload.base_lat is None or payload.base_lon is None):
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "Saha teknisyeni için base_lat/base_lon zorunlu (AI Service atama skorlaması için)"},
        )

    user = User(
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        specializations=payload.specializations,
        regions=payload.regions,
        base_lat=payload.base_lat,
        base_lon=payload.base_lon,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if user.role == "SAHA_TEKNISYENI":
        # AI Service'in team_profile cache'ini besler (bkz. ARCHITECTURE.md §7, §6.2).
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


@router.post("/login", response_model=ResponseEnvelope[TokenPair])
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    ip = request.client.host if request.client else None

    if payload.email is not None and payload.password is not None:
        user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
        if not user or not user.password_hash:
            await write_audit_log(
                db, user_id=None, action_type="LOGIN_FAILURE", result="FAILURE",
                ip_address=ip, detail={"email": payload.email},
            )
            raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "E-posta veya şifre hatalı"})

        if user.locked_until and user.locked_until > now:
            retry_after = int((user.locked_until - now).total_seconds())
            raise HTTPException(
                status_code=423,
                detail={"code": "ACCOUNT_LOCKED", "message": "Hesap kilitli", "retry_after_seconds": retry_after},
            )

        if not verify_password(payload.password, user.password_hash):
            user.failed_login_count += 1
            locked_now = user.failed_login_count >= LOCKOUT_THRESHOLD
            if locked_now:
                user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            await db.commit()
            await write_audit_log(
                db, user_id=user.id,
                action_type="ACCOUNT_LOCKED" if locked_now else "LOGIN_FAILURE",
                result="FAILURE", ip_address=ip,
            )
            if locked_now:
                raise HTTPException(
                    status_code=423,
                    detail={
                        "code": "ACCOUNT_LOCKED",
                        "message": "Çok fazla hatalı deneme, hesap kilitlendi",
                        "retry_after_seconds": LOCKOUT_MINUTES * 60,
                    },
                )
            raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "E-posta veya şifre hatalı"})

        user.failed_login_count = 0
        user.locked_until = None
        await db.commit()
        await write_audit_log(db, user_id=user.id, action_type="LOGIN_SUCCESS", result="SUCCESS", ip_address=ip)

    elif payload.gsm is not None and payload.otp is not None:
        if payload.otp != FIXED_OTP_CODE:
            raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "OTP kodu hatalı"})

        user = (await db.execute(select(User).where(User.gsm == payload.gsm))).scalar_one_or_none()
        if not user:
            # TASK_SPLIT.md §0: "login (kayıt/giriş)" tek adımda birleşik akış —
            # frontend'de ayrı bir müşteri kayıt ekranı yok, ilk girişte oluşturulur.
            user = User(
                role="MUSTERI",
                first_name="Müşteri",
                last_name=payload.gsm,
                gsm=payload.gsm,
                is_active=True,
            )
            db.add(user)
        elif not user.is_active:
            user.is_active = True
        await db.commit()

    else:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "{email,password} ya da {gsm,otp} gerekli"},
        )

    access_token, refresh_token = await _issue_token_pair(db, user)
    return ResponseEnvelope(success=True, data=TokenPair(access_token=access_token, refresh_token=refresh_token))


@router.post("/refresh", response_model=ResponseEnvelope[TokenPair])
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    token_hash = hash_token(payload.refresh_token)
    row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=401, detail={"code": "TOKEN_INVALID", "message": "Refresh token geçersiz"})

    if row.revoked_at is not None:
        # Reuse detection: daha önce kullanılmış (rotate edilmiş) bir token tekrar
        # geldi -> çalınma şüphesi, kullanıcının tüm oturumları iptal edilir.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
        raise HTTPException(
            status_code=401,
            detail={"code": "TOKEN_INVALID", "message": "Oturum çalınma şüphesi tespit edildi, tekrar giriş yapın"},
        )

    if row.expires_at < now:
        raise HTTPException(status_code=401, detail={"code": "TOKEN_EXPIRED", "message": "Refresh token süresi dolmuş"})

    user = await db.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": "TOKEN_INVALID", "message": "Kullanıcı bulunamadı"})

    new_access_token = create_access_token(user)
    new_raw_refresh = generate_refresh_token()
    new_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_raw_refresh),
        expires_at=now + timedelta(days=REFRESH_TOKEN_DAYS),
    )
    db.add(new_row)
    await db.flush()

    row.revoked_at = now
    row.replaced_by_token_id = new_row.id
    await db.commit()

    return ResponseEnvelope(success=True, data=TokenPair(access_token=new_access_token, refresh_token=new_raw_refresh))


@router.post("/logout", response_model=ResponseEnvelope[None])
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(payload.refresh_token)
    row = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None)))
    ).scalar_one_or_none()
    if row:
        row.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    return ResponseEnvelope(success=True, data=None)


@router.get("/me", response_model=ResponseEnvelope[UserPublic])
async def me(current_user: User = Depends(get_current_user)):
    return ResponseEnvelope(success=True, data=user_to_public(current_user))
