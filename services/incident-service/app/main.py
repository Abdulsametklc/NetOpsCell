import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.incidents import router as incidents_router
from app.core.config import settings
from app.core.sla_scheduler import run_scheduler

_background_tasks: list = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    _background_tasks.append(asyncio.create_task(run_scheduler()))
    yield
    for task in _background_tasks:
        task.cancel()


app = FastAPI(title="NetOpsCell - Incident Service", version="0.1.0", lifespan=lifespan)

app.include_router(incidents_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
