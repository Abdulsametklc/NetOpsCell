from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.internal import router as internal_router
from app.api.users import router as users_router
from app.core.database import async_session
from app.core.seed import seed_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session() as db:
        await seed_admin(db)
    yield


app = FastAPI(title="Identity Service", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(audit_router)
app.include_router(internal_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        error = detail
    else:
        error = {"code": "ERROR", "message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content={"success": False, "data": None, "error": error})


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
