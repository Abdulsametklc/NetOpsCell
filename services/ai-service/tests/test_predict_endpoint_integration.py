"""HTTP-seviyesi integration test: gercek FastAPI app + gercek Postgres uzerinden
POST /api/v1/ai/predict. app.core.database.engine, settings.database_url'e (yerelde
docker-compose'daki ai-db'ye - localhost:5434) baglanir; bu test CI'da ayni isimli bir
Postgres service container'i gerektirir (bkz. .github/workflows/ci.yml).

Bu test, gecmiste gercekten yasanan bir hatayi regresyona karsi kilitler: PredictionMethod
enum'ina ML_MODEL eklendiginde Postgres'teki prediction_method ENUM tipi guncellenmemisti
("invalid input value for enum prediction_method: ML_MODEL") - alembic migration 0002 ile
duzeltildi (bkz. docs/ml-model.md SS6.3).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _telemetry_payload(**overrides) -> dict:
    base = {
        "station_code": "IST-INTEGRATION-TEST",
        "lat": 41.0082,
        "lng": 28.9784,
        "signal_strength": -95.0,
        "packet_loss": 30.0,
        "temperature": 90.0,
        "power_status": "KESINTIDE",
        "recent_fault_count": 2,
    }
    base.update(overrides)
    return base


@pytest.mark.integration
def test_predict_endpoint_gercek_db_ile_basariyla_kaydeder():
    """ANTHROPIC_API_KEY tanimli olmadigi icin (varsayilan test ortami) ML modeli
    fallback yolu devreye girer; sonuc gercekten Postgres'e yazilir (200 donmesi,
    DB commit'inin basarili oldugunun kaniti - enum uyusmazliginda 500 donerdi)."""
    response = client.post("/api/v1/ai/predict", json=_telemetry_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["method"] in ("ML_MODEL", "LLM")
    assert body["data"]["fault_type"] in (
        "DONANIM", "GUC_KESINTISI", "BAGLANTI", "YAZILIM", "ISINMA", "BELIRSIZ",
    )
    assert 0.0 <= body["data"]["probability"] <= 1.0


@pytest.mark.integration
def test_predict_endpoint_farkli_girdiler_farkli_sonuc_verir():
    normal = client.post("/api/v1/ai/predict", json=_telemetry_payload(
        signal_strength=-60, packet_loss=0, temperature=22, power_status="NORMAL", recent_fault_count=0,
    ))
    critical = client.post("/api/v1/ai/predict", json=_telemetry_payload())

    assert normal.status_code == 200
    assert critical.status_code == 200
    assert normal.json()["data"]["probability"] != critical.json()["data"]["probability"]
