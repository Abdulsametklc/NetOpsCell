import httpx

from app.core.config import settings

_public_key_pem: str | None = None


async def get_public_key(force_refresh: bool = False) -> str:
    """Identity Service'in RS256 public key'ini önbelleğe alır. Servis yeniden
    başlayınca (in-memory keypair) anahtar değişir; force_refresh ile yenilenir
    (bkz. app/core/jwt_verify.py - imza hatasında bir kez otomatik yenilenir)."""
    global _public_key_pem
    if _public_key_pem is None or force_refresh:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.identity_service_url}/internal/public-key")
            resp.raise_for_status()
            _public_key_pem = resp.json()["public_key_pem"]
    return _public_key_pem
