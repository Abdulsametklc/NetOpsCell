from app.models.user import User
from app.schemas.auth import UserPublic


def user_to_public(user: User) -> UserPublic:
    """UserPublic(**user.__dict__) yerine: specializations/regions DB'de NULL
    olabilir (örn. seed edilen admin, MUSTERI kullanıcılar) ama şema list[str]
    bekliyor - None -> [] dönüşümü burada tek yerden yapılır."""
    return UserPublic(
        id=user.id,
        role=user.role,
        first_name=user.first_name,
        last_name=user.last_name,
        gsm=user.gsm,
        email=user.email,
        specializations=user.specializations or [],
        regions=user.regions or [],
    )
