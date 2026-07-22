from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User


async def seed_admin(db: AsyncSession) -> None:
    """POST /auth/personnel Admin rolü ister ama ilk admin'i oluşturacak kimse
    yok (chicken-and-egg) — bu yüzden başlangıçta ADMIN_EMAIL/ADMIN_PASSWORD
    env değişkenleriyle tek bir admin kullanıcı tohumlanır."""
    existing = (
        await db.execute(select(User).where(User.email == settings.admin_email))
    ).scalar_one_or_none()
    if existing:
        return

    db.add(
        User(
            role="ADMIN",
            first_name="Admin",
            last_name="User",
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            is_active=True,
        )
    )
    await db.commit()
