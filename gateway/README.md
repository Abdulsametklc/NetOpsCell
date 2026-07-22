# API Gateway

Sistemin tek giriş noktası. İş mantığı içermez; routing, RS256 JWT doğrulama, `X-User-*` header enjeksiyonu ve Redis tabanlı rate limiting yapar. Mimari gerekçe için kök [ARCHITECTURE.md](../ARCHITECTURE.md) §5.

## Sorumluluk

- **Routing:** path prefix'e göre isteği ilgili servise yönlendirir (aşağıdaki tablo)
- **JWT doğrulama:** Identity Service'in `/internal/public-key` ucundan aldığı RS256 public key ile imzayı doğrular; geçersiz/süresi dolmuş token'da `401` döner
- **Header enjeksiyonu:** doğrulanan JWT payload'ından `X-User-Id`, `X-User-Role`, `X-User-Specializations`, `X-User-Regions` header'larını downstream servise ekler
- **Spoofing koruması:** istemciden gelen `X-User-*` header'ları her zaman önce silinir, sadece Gateway'in kendisi (doğrulama sonrası) yeniden yazar
- **Rate limiting:** Redis tabanlı sabit pencere — `/auth/login` için IP başına 10/dk, genel trafik için IP başına 100/dk

## Routing Tablosu

| Path Prefix | Hedef | Auth |
|---|---|---|
| `/api/v1/auth/register/customer`, `/otp/verify`, `/login`, `/refresh` | Identity Service | Public |
| `/api/v1/auth/**` (diğerleri) | Identity Service | JWT zorunlu |
| `/api/v1/telemetry` | Incident Service | Public (simülatör) |
| `/api/v1/incidents/**` | Incident Service | JWT zorunlu |
| `/api/v1/ai/**` | AI Service | JWT zorunlu |
| `/api/v1/game/**` | Gamification Service | JWT zorunlu |
| `/health` | Gateway'in kendisi | — |

`/internal/**` (public-key, audit) Gateway'in routing tablosuna **dahil değildir** — sadece Docker iç ağından servis-servise çağrılır.

## Environment Değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `IDENTITY_SERVICE_URL` | `http://identity-service:8001` | |
| `INCIDENT_SERVICE_URL` | `http://incident-service:8002` | |
| `AI_SERVICE_URL` | `http://ai-service:8003` | |
| `GAMIFICATION_SERVICE_URL` | `http://gamification-service:8004` | |
| `REDIS_URL` | `redis://redis:6379/0` | Rate limit sayaçları |
| `FRONTEND_ORIGINS` | `http://localhost:5173,http://localhost:3000` | CORS izinli origin'ler |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | |
| `RATE_LIMIT_GENERAL_PER_MINUTE` | `100` | |

## Yerel Geliştirme

```bash
docker compose up --build gateway
```

Gateway durumsuzdur (stateless) — kendi veritabanı yoktur, migration gerekmez. Health check: `http://localhost:8000/health`.

## Bilinen Sınır

Notification Hub (`WS /api/v1/ws/notifications`) henüz bu serviste değil — planlı ama tamamlanmamış bir sonraki adım.
