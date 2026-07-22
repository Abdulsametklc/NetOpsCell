from contextlib import asynccontextmanager

import httpx
import jwt
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.consumers.notification_consumer import start_consumers
from app.core.config import settings
from app.core.jwt_verify import verify_token
from app.core.rate_limit import check_rate_limit
from app.core.routing import is_public, resolve_upstream
from app.core.ws_manager import manager

_background_tasks: list = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    _background_tasks.extend(await start_consumers())
    yield
    for task in _background_tasks:
        task.cancel()


app = FastAPI(title="NetOpsCell Gateway", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_client = httpx.AsyncClient(timeout=10.0)

# Bu header'lar asla istemciden gelen haliyle downstream'e taşınmaz - sadece
# Gateway'in kendisi, JWT'yi doğruladıktan SONRA yeniden yazar. Aksi halde bir
# istemci "X-User-Role: ADMIN" header'ını elle ekleyip RBAC'ı atlatabilirdi.
SPOOFABLE_HEADERS = {"x-user-id", "x-user-role", "x-user-specializations", "x-user-regions"}
HOP_BY_HOP_HEADERS = {"connection", "keep-alive", "transfer-encoding", "upgrade", "content-length", "content-encoding", "host"}

_HEALTH_TARGETS = {
    "identity": settings.identity_service_url,
    "incident": settings.incident_service_url,
    "ai": settings.ai_service_url,
    "gamification": settings.gamification_service_url,
}


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "data": None, "error": {"code": code, "message": message}})


@app.get("/health")
async def health():
    """ARCHITECTURE.md §5 madde 5 / TASK_SPLIT.md CP5: tüm servislerin health
    durumunu agregasyon. Bir servis çökse bile Gateway kendisi ayakta kalır ve
    hangi servisin çöktüğünü raporlar (bağımsızlık ilkesi)."""
    services: dict[str, str] = {}
    for name, base_url in _HEALTH_TARGETS.items():
        try:
            resp = await _client.get(f"{base_url}/health", timeout=3.0)
            services[name] = "healthy" if resp.status_code == 200 else "unhealthy"
        except httpx.RequestError:
            services[name] = "unreachable"

    overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"
    return {"status": overall, "services": services}


@app.websocket("/api/v1/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: str = Query(...)):
    """ARCHITECTURE.md §5 madde 4 - Notification Hub. JWT'den user_id/role
    çözülür, ilgili event'ler (badge.earned, game.points_awarded, kendi
    incident.assigned'ı, süpervizör/admin için incident.sla_breached) bu
    bağlantıya filtrelenerek gönderilir (bkz. app/consumers/notification_consumer.py)."""
    try:
        payload = await verify_token(token)
    except jwt.InvalidTokenError:
        await websocket.close(code=4401)
        return

    user_id = str(payload.get("sub", ""))
    role = str(payload.get("role", ""))

    await manager.connect(user_id, role, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive / bağlantı kopuşunu yakalar
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(full_path: str, request: Request):
    path = "/" + full_path
    upstream = resolve_upstream(path)
    if upstream is None:
        return _error(404, "NOT_FOUND", "Bilinmeyen route")

    client_ip = request.client.host if request.client else "unknown"
    is_login = request.method == "POST" and path == "/api/v1/auth/login"
    bucket, limit = (
        ("login", settings.rate_limit_login_per_minute)
        if is_login
        else ("general", settings.rate_limit_general_per_minute)
    )
    if not await check_rate_limit(client_ip, bucket, limit):
        return _error(429, "RATE_LIMITED", "Çok fazla istek, lütfen bekleyin")

    forward_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() not in SPOOFABLE_HEADERS
    }

    if not is_public(request.method, path):
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return _error(401, "TOKEN_INVALID", "Authorization header eksik")
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = await verify_token(token)
        except jwt.ExpiredSignatureError:
            return _error(401, "TOKEN_EXPIRED", "Token süresi dolmuş")
        except jwt.InvalidTokenError:
            return _error(401, "TOKEN_INVALID", "Token geçersiz")

        forward_headers["X-User-Id"] = str(payload.get("sub", ""))
        forward_headers["X-User-Role"] = str(payload.get("role", ""))
        forward_headers["X-User-Specializations"] = ",".join(payload.get("specializations") or [])
        forward_headers["X-User-Regions"] = ",".join(payload.get("regions") or [])

    body = await request.body()
    try:
        upstream_response = await _client.request(
            request.method,
            f"{upstream}{path}",
            params=list(request.query_params.multi_items()),
            headers=forward_headers,
            content=body,
        )
    except httpx.RequestError:
        return _error(503, "SERVICE_UNAVAILABLE", "Hedef servise ulaşılamıyor")

    response_headers = {k: v for k, v in upstream_response.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )
