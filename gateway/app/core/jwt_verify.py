import jwt

from app.core.public_key import get_public_key


async def verify_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError. İmza hatasında
    (identity-service yeniden başlamış, anahtar değişmiş olabilir) bir kez public
    key'i yenileyip tekrar dener; gerçekten geçersiz/sahte bir token bu ikinci
    denemede de aynı şekilde reddedilir."""
    key = await get_public_key()
    try:
        return jwt.decode(token, key, algorithms=["RS256"])
    except jwt.InvalidSignatureError:
        key = await get_public_key(force_refresh=True)
        return jwt.decode(token, key, algorithms=["RS256"])
