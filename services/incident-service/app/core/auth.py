import uuid

from fastapi import Header, HTTPException, status


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
