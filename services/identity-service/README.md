# Identity Service

Kayıt, giriş, token yönetimi, rol/yetki, audit log ve hesap kilitleme. Mimari kararların gerekçesi için kök dizindeki [ARCHITECTURE.md](../../ARCHITECTURE.md) §3/§4.1, ortak sözleşmeler için [docs/CONTRACTS.md](../../docs/CONTRACTS.md).

## Sorumluluk

- Müşteri kaydı (GSM + OTP, simülasyon kodu her zaman `1234`) ve personel hesabı oluşturma (Admin)
- Giriş: personel (e-posta + şifre) ve müşteri (GSM + OTP) tek `/auth/login` ucundan
- RS256 imzalı access token (15dk) + opaque refresh token (7 gün, DB'de hash'lenmiş, rotation zinciri)
- Refresh token reuse detection: geçersiz kılınmış bir token tekrar kullanılırsa kullanıcının **tüm** oturumları iptal edilir
- Hesap kilitleme: 5 başarısız girişte 15 dakika
- Şifre politikası (min 8 karakter, büyük harf, rakam, özel karakter) + argon2 hash
- Audit log: giriş başarılı/başarısız, hesap kilitlenmesi, rol değişikliği, yetkisiz erişim (403)
- Rol/yetki matrisi: `Depends(require_roles([...]))` deseni ile endpoint seviyesinde uygulanır

## Endpoint Listesi

| Method | Path | Rol | Açıklama |
|---|---|---|---|
| POST | `/api/v1/auth/register/customer` | Public | GSM + ad/soyad → OTP gönderir |
| POST | `/api/v1/auth/otp/verify` | Public | GSM + kod → hesabı aktive eder, token çifti döner |
| POST | `/api/v1/auth/personnel` | Admin | Personel hesabı oluşturur (rol/uzmanlık/bölge/konum) |
| POST | `/api/v1/auth/login` | Public | `{email,password}` ya da `{gsm,otp}` |
| POST | `/api/v1/auth/refresh` | Public (refresh token ile) | Token rotation |
| POST | `/api/v1/auth/logout` | Authenticated | Refresh token iptali |
| GET | `/api/v1/auth/me` | Authenticated | JWT'den profil |
| GET | `/api/v1/auth/users` | Admin, Süpervizör | Filtreli personel listesi |
| PATCH | `/api/v1/auth/users/{id}` | Admin | Rol/uzmanlık/bölge/konum/aktiflik günceller → `identity.personnel.upserted` event yayınlar |
| GET | `/api/v1/auth/audit-logs` | Admin | Filtreli audit log |
| GET | `/internal/public-key` | Internal (Gateway) | RS256 public key PEM — Gateway JWT doğrulaması için |
| POST | `/internal/audit` | Internal (diğer servisler) | Kendi 403'lerini merkezi audit log'a yazar |
| GET | `/health` | — | Health check |

Standart response formatı: `{ "success": bool, "data": ..., "error": {...} | null }`. Swagger/OpenAPI: `http://localhost:8001/docs`.

**`/internal/**` uçları Gateway'in routing tablosuna dahil değildir** — sadece Docker iç ağından (`netopscell-net`) diğer servisler tarafından çağrılır.

## Environment Değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@identity-db:5432/identity_db` | Postgres bağlantısı |
| `REDIS_URL` | `redis://redis:6379/0` | `identity.personnel.upserted` event publisher |
| `JWT_SECRET` | — | Kullanılmıyor (RS256 keypair process içinde üretilir); geriye dönük uyumluluk için tutuluyor |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token ömrü |
| `OTP_EXPIRE_MINUTES` | `5` | OTP kodu geçerlilik süresi |
| `ADMIN_EMAIL` | `admin@netopscell.local` | İlk açılışta tohumlanan admin hesabı |
| `ADMIN_PASSWORD` | `Admin123!` | İlk admin şifresi |

**Not — RS256 keypair:** Container her yeniden başladığında yeni bir RSA keypair üretilir (process-içi, kalıcı değil). Bu, container restart'ında tüm outstanding access/refresh token'ların geçersiz kalacağı (kullanıcıların tekrar login olması gerekeceği) anlamına gelir — hackathon kapsamı için kabul edilebilir bir basitleştirme.

## Yerel Geliştirme

```bash
docker compose up --build identity-service

# Migration'lar container başlarken otomatik uygulanır (docker-entrypoint.sh)
docker compose exec identity-service alembic upgrade head
```

## Veritabanı Şeması

`users`, `refresh_tokens`, `otp_codes`, `audit_logs` — tam kolon listesi için `app/models/`.
