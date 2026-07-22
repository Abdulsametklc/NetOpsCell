from fastapi import FastAPI

from app.api.ai import router as ai_router
from app.core.config import settings

app = FastAPI(title="NetOpsCell - AI Service", version="0.1.0")

app.include_router(ai_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
