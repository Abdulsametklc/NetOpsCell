# Gamification Service

Saha ekibi motivasyon sistemi: puan, rozet, seviye, liderlik tablosu. **Doğrudan hiçbir endpoint tetiklemez** — tamamen Incident Service'ten gelen event'lerle çalışır (case'in "olay tabanlı mimari beklenir" şartı, bkz. [ARCHITECTURE.md](../../ARCHITECTURE.md) §9).

## Sorumluluk

- Incident Service event'lerini tüketip puan hesabı yapar, `user_stats`'ı günceller
- Rozet koşullarını kontrol eder, kazanıldığında `user_badges`'e yazar
- Liderlik tablosu ve profil verisini sunar

## Puan Tablosu

| Olay | Puan | Koşul |
|---|---|---|
| Arıza çözüldü | +10 | Her çözüm |
| Hızlı müdahale bonusu | +5 | Çözüm süresi SLA'nın yarısından kısa |
| KRİTİK arıza SLA içinde çözüldü | +10 | `priority=KRITIK` ve SLA süresi içinde |
| Kalıcı çözüm | +15 | NOC değerlendirmesi `is_permanent=true` |
| Geçici çözüm | -3 | NOC değerlendirmesi `is_permanent=false` |
| SLA aşımı | -5 | Her aşım (atanmamış vakada ceza yok) |
| Tekrar eden arıza | -3 | Aynı istasyonda 24 saat içinde ikinci vaka — önceki çözümü yapan kişiye yazılır, "temiz çözüm serisi"ni sıfırlar |

SLA süreleri (`SLA_DURATIONS`) Incident Service'in kendi SLA scheduler'ından **bağımsız**, statik bir sabit olarak burada da tutulur — ikisi de aynı case tablosuna (§4.4) dayanır, ama Gamification'ın puan hesabı Incident Service'in `sla_due_at` alanının doldurulmuş olmasını beklemez.

## Rozetler

| Rozet | Koşul | Durum |
|---|---|---|
| İlk Müdahale | İlk arızayı çözme | Uçtan uca test edildi |
| Hız Ustası | SLA'nın yarısında 10 müdahale | Kod incelemesiyle doğrulandı (eşik yüksek, canlı tetiklenemedi) |
| Kriz Yöneticisi | 10 KRİTİK arızayı SLA içinde çözme | Kod incelemesiyle doğrulandı |
| Maratoncu | Bir günde 15 arıza çözümü | Kod incelemesiyle doğrulandı |
| Uzman | Tek türde 50 arıza çözümü | Kod incelemesiyle doğrulandı |
| Kalıcı Çözüm | 20 arızada tekrar olmadan (temiz seri) | Kod incelemesiyle doğrulandı |

> Case'in orijinal PDF'indeki rozet-adı/koşul tablosu OCR kayması nedeniyle satır satır bozuk geldi; isim↔koşul eşleşmesi ARCHITECTURE.md §9'da anlamsal olarak yeniden kuruldu (örn. "Hız" → SLA yarısında hız, "Kriz" → KRİTİK öncelik).

## Seviye Sistemi

| Seviye | Puan Aralığı |
|---|---|
| Bronz | 0-499 |
| Gümüş | 500-1499 |
| Altın | 1500-2999 |
| Platin | 3000+ |

## Endpoint Listesi

| Method | Path | Açıklama |
|---|---|---|
| GET | `/api/v1/game/leaderboard?period=daily\|weekly&limit=10` | Liderlik tablosu (şu an dönem filtresi uygulanmıyor — tüm zamanlar) |
| GET | `/api/v1/game/profile/{user_id}` | Toplam puan, seviye, çözülen vaka, ortalama puan |
| GET | `/health` | Health check |

Swagger/OpenAPI: `http://localhost:8004/docs`.

## Event Tüketimi (Redis Streams)

| Event | Etki |
|---|---|
| `incident.created` | Tekrar eden arıza tespiti (-3 ceza + seri sıfırlama) |
| `incident.resolved` | Puan ekleme (+10/+5/+10), rozet kontrolü, istasyon-çözüm log güncelleme |
| `incident.evaluated` | +15/-3 kalıcı/geçici çözüm bonusu |
| `incident.sla_breached` | -5 ceza |

## Environment Değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `SERVICE_NAME` | `gamification-service` | Health check yanıtında görünen servis adı |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@game-db:5432/game_db` | Postgres bağlantısı |
| `REDIS_URL` | `redis://redis:6379/0` | Event consumer (Redis Streams) |

## Yerel Geliştirme

```bash
docker compose up --build gamification-service

# Manuel migration:
docker compose exec gamification-service alembic upgrade head
```

## Veritabanı Şeması

`point_ledger`, `user_stats`, `badges`, `user_badges`, `station_resolution_log`, `fault_type_resolution_counts` — tam kolon listesi için `app/models/`.

## Bilinmeyen Kısım

`game.points_awarded` ve `badge.earned` event'leri tasarlandı (bkz. [EVENTS.md](../../EVENTS.md)) ama henüz yayınlanmıyor — bunların tüketicisi olan Gateway Notification Hub'ı (gerçek zamanlı bildirim, bonus +2) henüz kurulmadı.
