import asyncio

import httpx

from app.core.config import settings
from app.schemas.contracts import PredictResponse, TelemetryInput

TIMEOUT_SECONDS = 2.0
RETRY_DELAY_SECONDS = 0.2


class AIServiceUnavailable(Exception):
    """AI Service'e ulasilamadi: baglanti hatasi, zaman asimi ya da 1 retry sonrasi da basarisiz.
    Cagiran taraf (Incident Service) bu durumda case kurali geregi vakayi BELIRSIZ/ORTA ile
    olusturup manuel atama kuyruguna dusurmelidir (bkz. ARCHITECTURE.md SS4.2)."""


async def predict(payload: TelemetryInput) -> PredictResponse:
    last_error: Exception | None = None
    for attempt in range(2):  # ilk deneme + 1 retry
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{settings.ai_service_url}/api/v1/ai/predict",
                    json=payload.model_dump(mode="json"),
                )
                response.raise_for_status()
                # AI Service, sistem genelindeki standart {success, data, error} zarfini
                # kullanir (bkz. ARCHITECTURE.md SS8.2) - asil PredictResponse "data" altinda.
                envelope = response.json()
                return PredictResponse.model_validate(envelope["data"])
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
            last_error = exc
            if attempt == 0:
                await asyncio.sleep(RETRY_DELAY_SECONDS)

    raise AIServiceUnavailable(str(last_error))
