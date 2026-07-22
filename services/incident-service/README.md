# Incident Service

Arıza vakalarının yaşam döngüsünü yönetir: telemetri girişi, AI Service ile senkron tahmin/atama entegrasyonu, durum makinesi, SLA takibi, saha iletişimi ve çözüm değerlendirmesi. Mimari kararların gerekçesi için kök dizindeki [ARCHITECTURE.md](../../ARCHITECTURE.md) §4.2, event detayları için [EVENTS.md](../../EVENTS.md).

## Sorumluluk

- Telemetri girdisini kabul eder, AI Service'in `/predict` ve `/assign` uçlarını senkron çağırır
- 7 durumlu arıza yaşam döngüsünü (`YENI → ATANDI → YOLDA → MÜDAHALE_EDİLİYOR → PARÇA_BEKLENİYOR → ÇÖZÜLDÜ → KAPANDI`) doğrular ve uygular
- SLA sürelerini hesaplar, arka planda periyodik olarak SLA aşımını tespit eder
- Saha teknisyeni ↔ NOC operatörü mesajlaşma thread'ini tutar
- AI Service'e ve Gamification Service'e olay (event) yayınlar (Redis Streams)

**Bağımsızlık:** AI Service'e ulaşılamadığında (bağlantı hatası/timeout, 1 retry sonrası) vaka `BELİRSİZ`/`ORTA` ile açılır, manuel atama kuyruğuna düşer — servis hiçbir zaman 500 dönüp isteği reddetmez.

## Endpoint Listesi

| Method | Path | Rol | Açıklama |
|---|---|---|---|
| POST | `/api/v1/telemetry` | — | Telemetri girişi → AI tahmini + otomatik atama denemesi |
| GET | `/api/v1/incidents` | — | Tüm vakalar (rol bazlı filtreleme henüz CP6 kapsamına girmedi) |
| GET | `/api/v1/incidents/queue/unassigned` | — | Atanmamış/kuyrukta bekleyen vakalar |
| GET | `/api/v1/incidents/stats/summary` | — | Süpervizör Dashboard agregasyonları (tür/öncelik dağılımı, SLA uyumu, ortalama müdahale süresi) |
| GET | `/api/v1/incidents/{id}` | — | Vaka detayı |
| PATCH | `/api/v1/incidents/{id}/status` | Durum makinesine göre (auth header zorunlu) | Durum geçişi; `COZULDU` için çözüm notu zorunlu |
| POST | `/api/v1/incidents/{id}/messages` | Atanan Saha Teknisyeni, NOC Operatörü | Vaka içi mesaj (thread) |
| GET | `/api/v1/incidents/{id}/messages` | — | Mesaj geçmişi |
| POST | `/api/v1/incidents/{id}/resolution-note` | Atanan Saha Teknisyeni | COZULDU'dan bağımsız ek çözüm notu |
| POST | `/api/v1/incidents/{id}/evaluation` | NOC Operatörü | 1-5 yıldız değerlendirme (sadece `KAPANDI` sonrası, tek seferlik) |
| PATCH | `/api/v1/incidents/{id}/fault-type` | NOC Operatörü, Süpervizör | AI'nin atadığı türü değiştirir (doğruluk metriği için AI Service'e bildirilir) |
| PATCH | `/api/v1/incidents/{id}/assign` | Süpervizör, Admin | Manuel atama (sadece `YENI` durumundaki vakalar) |
| GET | `/health` | — | Health check |

Standart response formatı: `{ "success": bool, "data": ..., "error": {...} | null }`. Swagger/OpenAPI: `http://localhost:8002/docs`.

## Auth Notu

Rol gerektiren endpoint'ler `X-User-Id` ve `X-User-Role` header'larını okur (bkz. `app/core/auth.py`). Bu header'lar artık Gateway tarafından, JWT doğrulamasından sonra otomatik ekleniyor (bkz. [gateway/README.md](../../gateway/README.md)) — servise doğrudan (Gateway'siz) istek atılırsa bu header'lar elle gönderilmelidir.

## Environment Değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `SERVICE_NAME` | `incident-service` | Health check yanıtında görünen servis adı |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@incident-db:5432/incident_db` | Postgres bağlantısı |
| `AI_SERVICE_URL` | `http://ai-service:8003` | AI Service'in senkron `/predict`, `/assign` uçları |
| `REDIS_URL` | `redis://redis:6379/0` | Event publisher (Redis Streams) |

## Yerel Geliştirme

```bash
# Docker Compose ile (önerilen)
docker compose up --build incident-service

# Migration'lar container başlarken otomatik uygulanır (docker-entrypoint.sh)
# Manuel migration:
docker compose exec incident-service alembic upgrade head
```

## Veritabanı Şeması

`incidents`, `telemetry_readings`, `incident_status_history`, `incident_messages`, `incident_resolution_notes`, `incident_evaluations` — tam kolon listesi için `app/models/incident.py`.
