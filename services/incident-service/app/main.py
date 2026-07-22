from fastapi import FastAPI

from app.api.incidents import router as incidents_router
from app.core.config import settings

app = FastAPI(title="NetOpsCell - Incident Service", version="0.1.0")

app.include_router(incidents_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
