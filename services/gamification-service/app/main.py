from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.game import router as game_router
from app.consumers.skeleton import start_consumers
from app.core.config import settings

_background_tasks: list = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    _background_tasks.extend(await start_consumers())
    yield
    for task in _background_tasks:
        task.cancel()


app = FastAPI(title="NetOpsCell - Gamification Service", version="0.1.0", lifespan=lifespan)

app.include_router(game_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
