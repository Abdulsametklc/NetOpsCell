import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from passlib.context import CryptContext

from app.core.config import settings
from app.models.user import User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

FIXED_OTP_CODE = "1234"
REFRESH_TOKEN_DAYS = 7
LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15

# RS256 keypair: generated once per process. Gateway (CP3) verifies signatures
# with the public key only, never needs the private key (ARCHITECTURE.md §3.2).
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_KEY_PEM = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
PUBLIC_KEY_PEM = _private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def validate_password_strength(password: str) -> list[str]:
    violations = []
    if len(password) < 8:
        violations.append("min_length")
    if not re.search(r"[A-Z]", password):
        violations.append("uppercase")
    if not re.search(r"\d", password):
        violations.append("digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        violations.append("special_char")
    return violations


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "specializations": user.specializations or [],
        "regions": user.regions or [],
        "token_type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, _PRIVATE_KEY_PEM, algorithm="RS256")


def decode_access_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError on failure."""
    return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
