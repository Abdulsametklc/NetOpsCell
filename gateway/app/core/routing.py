from app.core.config import settings

# ARCHITECTURE.md §5.1 - Gateway Routing Tablosu
ROUTE_TABLE: list[tuple[str, str]] = [
    ("/api/v1/auth", settings.identity_service_url),
    ("/api/v1/telemetry", settings.incident_service_url),
    ("/api/v1/incidents", settings.incident_service_url),
    ("/api/v1/ai", settings.ai_service_url),
    ("/api/v1/game", settings.gamification_service_url),
]

# JWT doğrulaması gerektirmeyen tek uçlar (register/login/refresh + telemetri
# simülatörü). Geri kalan her şey Authorization: Bearer ister.
PUBLIC_ROUTES: set[tuple[str, str]] = {
    ("POST", "/api/v1/auth/register/customer"),
    ("POST", "/api/v1/auth/otp/verify"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/telemetry"),
}


def resolve_upstream(path: str) -> str | None:
    for prefix, base_url in ROUTE_TABLE:
        if path == prefix or path.startswith(prefix + "/"):
            return base_url
    return None


def is_public(method: str, path: str) -> bool:
    return (method, path) in PUBLIC_ROUTES
