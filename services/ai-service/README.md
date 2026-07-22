# AI Service

Case'in kalbi: arıza tahmini, arıza türü sınıflandırması ve akıllı saha ekibi ataması. Yaklaşım gerekçesi ve prompt tasarımı için [docs/ai-approach.md](../../docs/ai-approach.md), mimari için [ARCHITECTURE.md](../../ARCHITECTURE.md) §8.

## Sorumluluk

- **Görev 1+2 (tahmin + sınıflandırma):** LLM (Anthropic, forced tool-call) ile `probability` + `fault_type`; LLM kullanılamazsa girdiye göre gerçekten değişen kural tabanlı fallback devreye girer (asla sabit çıktı yok)
- **Eşik uygulaması:** `suggestion` (IZLE/VAKA_AC/ACIL) ve `priority`, LLM çıktısından bağımsız, deterministik kodda hesaplanır
- **Görev 3 (akıllı atama):** Haversine mesafe + uzmanlık eşleşme + kapasite skorlamasıyla (tamamen deterministik, LLM'siz) en uygun saha ekibini seçer
- **Doğruluk takibi:** NOC/Süpervizör düzeltmelerini (`incident.type_changed` event'i) tüketip `GET /accuracy`'de raporlar
- **Read-model cache'leri:** `team_profile` (Identity'den event ile senkron) ve `team_workload` (Incident'ten event ile senkron) — Identity/Incident Service'in DB'sine hiç doğrudan erişmez (database-per-service)

**Bağımsızlık:** LLM sağlayıcısına (dış API) ulaşılamazsa 1 retry + circuit breaker sonrası otomatik kural tabanlı fallback'e düşer. AI Service'in kendisine (bağlantı/timeout) ulaşılamaması durumu Incident Service tarafında ele alınır (vaka BELİRSİZ/ORTA ile açılır).

## Endpoint Listesi

| Method | Path | Çağıran | Açıklama |
|---|---|---|---|
| POST | `/api/v1/ai/predict` | Incident Service (senkron) | Telemetri → `{probability, fault_type, priority, suggestion, method, confidence_explanation}` |
| POST | `/api/v1/ai/assign` | Incident Service (senkron, vaka oluşturulduktan sonra) | `{incident_id, fault_type, priority, lat, lng}` → `{queued, team_id, team_name, score, components}` |
| GET | `/api/v1/ai/accuracy?breakdown=category` | Süpervizör Dashboard | `doğru/toplam*100` + kategori bazlı kırılım (bonus +3) |
| GET | `/health` | — | Health check |

Standart response formatı: `{ "success": bool, "data": ..., "error": {...} | null }`. Swagger/OpenAPI: `http://localhost:8003/docs`.

## Event Tüketimi (Redis Streams, arka planda)

| Event | Kaynak | Etki |
|---|---|---|
| `identity.personnel.upserted` | Identity Service | `team_profile` cache upsert |
| `incident.assigned` | Incident Service | `team_workload.active_incident_count` +1 |
| `incident.resolved` | Incident Service | `team_workload.active_incident_count` -1 |
| `incident.type_changed` | Incident Service | `accuracy_feedback` kaydı (`is_correct=false`) |

## Environment Değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `SERVICE_NAME` | `ai-service` | Health check yanıtında görünen servis adı |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@ai-db:5432/ai_db` | Postgres bağlantısı |
| `REDIS_URL` | `redis://redis:6379/0` | Event consumer (Redis Streams) |
| `ANTHROPIC_API_KEY` | *(boş)* | LLM entegrasyonu. **Boş bırakılırsa servis otomatik olarak kural tabanlı fallback'i kullanır — LLM olmadan da tam çalışır.** |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Kullanılacak model |
| `LLM_TIMEOUT_SECONDS` | `4.0` | LLM çağrısı için timeout |
| `LLM_CIRCUIT_BREAKER_THRESHOLD` | `3` | Art arda kaç başarısızlıktan sonra devre kesici açılır |
| `LLM_CIRCUIT_BREAKER_COOLDOWN_SECONDS` | `30.0` | Devre kesici açıkken ne kadar süre doğrudan fallback kullanılır |

## Yerel Geliştirme

```bash
docker compose up --build ai-service

# Manuel migration:
docker compose exec ai-service alembic upgrade head
```

## Veritabanı Şeması

`predictions`, `accuracy_feedback`, `team_profile`, `team_workload`, `assignment_log` — tam kolon listesi için `app/models/`.

## Bilinen Sınırlama

Bu depoda gerçek bir `ANTHROPIC_API_KEY` yapılandırılmadı; LLM'in başarılı-çağrı davranışı üretimde test edilmedi, sadece "anahtar yok → fallback" yolu doğrulandı. Detay için `docs/ai-approach.md` §8.
