import uuid

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "TOKEN_INVALID", "message": "Authorization header eksik"})

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"code": "TOKEN_EXPIRED", "message": "Token süresi dolmuş"})
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail={"code": "TOKEN_INVALID", "message": "Token geçersiz"})

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": "TOKEN_INVALID", "message": "Kullanıcı bulunamadı"})
    return user
