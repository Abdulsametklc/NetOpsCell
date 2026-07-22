# NetOpsCell — Event Kataloğu

Bu doküman, servisler arası **gerçekte uygulanmış** tüm event'leri ve örnek payload'larını listeler. Tasarım gerekçesi için [ARCHITECTURE.md](ARCHITECTURE.md) §6'ya, alan tipleri için [docs/CONTRACTS.md](docs/CONTRACTS.md)'ye bakın — bu dosya onların **"şu an gerçekten çalışıyor mu"** özeti ve kod referanslı halidir.

## Taşıma Katmanı

**Redis Streams.** Her event kendi stream'inde yayınlanır (`XADD <event_type> * data '<json>'`); stream key'i doğrudan `event_type` string'idir. Payload, tek bir `data` alanında JSON string olarak taşınır (nested/typed alanları ayrı stream field'larına bölmek yerine — bkz. `app/core/event_publisher.py` her serviste).

Her tüketici servis kendi servis adını consumer group olarak kullanır (`XGROUP CREATE <stream> <servis-adi> ...`, `mkstream=True`). Bu sayede bir servis event yayınlandığı anda kapalıysa, tekrar ayağa kalktığında `XREADGROUP` ile kaçırdığı event'leri okumaya devam eder — düz Pub/Sub'ın aksine event kaybolmaz (bkz. ARCHITECTURE.md §6.1).

---

## 1. Uygulanan Event'ler

### `identity.personnel.upserted`

**Yayınlayan:** Identity Service (`POST /auth/personnel`, sadece rol `SAHA_TEKNISYENI` olduğunda — atama algoritmasının ihtiyaç duyduğu tek rol)
**Tüketen:** AI Service (`team_profile` read-model cache'i günceller)

```json
{
  "event_type": "identity.personnel.upserted",
  "user_id": "44444444-4444-4444-4444-444444444444",
  "name": "Ahmet Yılmaz",
  "specializations": ["ISINMA", "BAGLANTI"],
  "regions": ["IST-AVRUPA"],
  "base_lat": 41.021,
  "base_lon": 29.031,
  "is_active": true
}
```

### `incident.created`

**Yayınlayan:** Incident Service (`POST /telemetry` → vaka oluşturulduğu her an, hem AI tahmini hem BELİRSİZ/ORTA fallback yolu dahil)
**Tüketen:** Gamification Service (tekrar eden arıza tespiti — bkz. §6.1)

```json
{
  "event_type": "incident.created",
  "incident_id": "9fbc69a2-fae8-40d6-8b18-addd170fc725",
  "incident_number": "INC-2026-000005",
  "station_code": "IST-1000",
  "fault_type": "ISINMA",
  "priority": "ORTA",
  "probability": 0.65,
  "created_at": "2026-07-22T18:03:42.459038+00:00"
}
```

### `incident.assigned`

**Yayınlayan:** Incident Service — iki kaynaktan: (a) `POST /telemetry` içinde AI'nin otomatik atamasından sonra (`assigned_by="SYSTEM"`), (b) `PATCH /incidents/{id}/assign` manuel atamadan sonra (`assigned_by=<süpervizör user_id>`)
**Tüketen:** AI Service (`team_workload.active_incident_count` +1 — boşluk_oranı girdisi)

```json
{
  "event_type": "incident.assigned",
  "incident_id": "9fbc69a2-fae8-40d6-8b18-addd170fc725",
  "team_id": "44444444-4444-4444-4444-444444444444",
  "team_name": "Test Teknisyen",
  "score": 0.999,
  "assigned_by": "SYSTEM",
  "assigned_at": "2026-07-22T18:03:42.6Z"
}
```

### `incident.resolved`

**Yayınlayan:** Incident Service (`PATCH /incidents/{id}/status`, hedef `COZULDU` olduğunda)
**Tüketen:** AI Service (`team_workload` -1), Gamification Service (puan hesabı + rozet kontrolü + istasyon çözüm log'u)

> **Not:** `station_code` alanı ARCHITECTURE.md'nin ilk taslağında yoktu; CP5'te tekrar-eden-arıza tespiti için eklendi (bkz. `docs/CONTRACTS.md` değişiklik notu).

```json
{
  "event_type": "incident.resolved",
  "incident_id": "9fbc69a2-fae8-40d6-8b18-addd170fc725",
  "team_id": "44444444-4444-4444-4444-444444444444",
  "station_code": "IST-1000",
  "fault_type": "ISINMA",
  "priority": "ORTA",
  "created_at": "2026-07-22T18:03:42.459038+00:00",
  "resolved_at": "2026-07-22T18:04:08.743494+00:00"
}
```

### `incident.evaluated`

**Yayınlayan:** Incident Service (`POST /incidents/{id}/evaluation`, sadece vaka `KAPANDI` durumundayken, tek seferlik)
**Tüketen:** Gamification Service (+15 kalıcı çözüm / -3 geçici çözüm — çözümü yapan kişi, aynı `incident_id`'ye ait `incident.resolved` `point_ledger` kaydından bulunur, çünkü bu event kimin çözdüğünü taşımaz)

```json
{
  "event_type": "incident.evaluated",
  "incident_id": "9fbc69a2-fae8-40d6-8b18-addd170fc725",
  "stars": 5,
  "is_permanent": true,
  "evaluated_by": "66666666-6666-6666-6666-666666666666"
}
```

### `incident.type_changed`

**Yayınlayan:** Incident Service (`PATCH /incidents/{id}/fault-type`, NOC Operatörü/Süpervizör override yaptığında)
**Tüketen:** AI Service (`accuracy_feedback` tablosuna `is_correct=false` kaydı — `GET /ai/accuracy` metriğinin girdisi)

```json
{
  "event_type": "incident.type_changed",
  "incident_id": "9fbc69a2-fae8-40d6-8b18-addd170fc725",
  "original_fault_type": "ISINMA",
  "new_fault_type": "DONANIM",
  "changed_by": "66666666-6666-6666-6666-666666666666",
  "changed_at": "2026-07-22T18:10:00Z"
}
```

### `incident.sla_breached`

**Yayınlayan:** Incident Service — arka plan görevi (`sla_scheduler.py`, 30sn periyodik), `sla_due_at` geçmiş ve hâlâ aktif (`COZULDU`/`KAPANDI` değil) vakalar için
**Tüketen:** Gamification Service (-5 ceza, `team_id` boşsa — yani vaka hâlâ atanmamışsa — ceza uygulanmaz)

> **Not:** `team_id` alanı da CP5'te eklendi (cezanın kime yazılacağını bilmek için gerekliydi).

```json
{
  "event_type": "incident.sla_breached",
  "incident_id": "d6530e83-2d36-4686-8292-46b0d8635667",
  "team_id": "44444444-4444-4444-4444-444444444444",
  "priority": "KRITIK",
  "sla_due_at": "2026-07-22T19:21:19.055393+00:00",
  "breached_at": "2026-07-22T19:22:00Z"
}
```

---

## 2. Tasarlanan Ama Henüz Yayınlanmayan Event'ler

Bu event'ler `docs/CONTRACTS.md`'de şema olarak tanımlı ve mimari gerekçesi ARCHITECTURE.md'de var, ama şu an **hiçbir servis bunları yayınlamıyor** — dürüstlük ilkesiyle burada açıkça belirtiyoruz:

| Event | Neden yayınlanmıyor |
|---|---|
| `incident.status_changed` (genel) | Sadece gerçek tüketicisi olan geçişler event'e döküldü (`incident.assigned`, `incident.resolved`); ara durumlar (YOLDA, MUDAHALE_EDİLİYOR, PARÇA_BEKLENİYOR, KAPANDI) şu an sadece DB'ye yazılıyor, event yayınlamıyor. Bir tüketici ihtiyacı doğarsa (örn. Notification Hub) eklenmesi kolay — `PATCH /incidents/{id}/status` zaten tek bir merkezi yerde. |
| `incident.part.fulfilled` | PARÇA_BEKLENİYOR→MÜDAHALE_EDİLİYOR geçişi state machine'de var ama bu geçişi tetikleyecek bir parça-tedarik entegrasyonu (envanter sistemi) case kapsamında hiç yok; sadece SYSTEM rolüyle genel status endpoint'i üzerinden tetiklenebilir durumda. |
| `ai.prediction.completed` | `/ai/predict` tamamen senkron REST cevabı olarak tasarlandı (Incident Service zaten sonucu response'ta alıyor); ek bir analitik event'i olarak yayınlamak şu an gereksiz görüldü. |
| `game.points_awarded`, `badge.earned` | Bu event'ler Gateway'in **Notification Hub**'ı (gerçek zamanlı bildirim, bonus +2) tarafından tüketilecek şekilde tasarlandı. Notification Hub henüz kurulmadı (Kişi 1'in Gateway kapsamında), bu yüzden yayınlayıcı taraf da henüz eklenmedi — tüketicisi olmayan bir event yayınlamanın faydası yok. Gateway hazır olduğunda `gamification-service/app/consumers/handlers.py`'deki ilgili `# TODO` yorumlarına bakın. |

---

## 3. Yayıncı/Tüketici Hızlı Referans

| Event | Yayınlayan | Tüketen |
|---|---|---|
| `identity.personnel.upserted` | Identity | AI |
| `incident.created` | Incident | Gamification |
| `incident.assigned` | Incident | AI |
| `incident.resolved` | Incident | AI, Gamification |
| `incident.evaluated` | Incident | Gamification |
| `incident.type_changed` | Incident | AI |
| `incident.sla_breached` | Incident | Gamification |

## 4. Dayanıklılık Notu

Her tüketici, event işlerken hata alırsa (`app/consumers/*.py` içindeki `try/except`) hatayı loglar ama yine de `XACK` çağırır — yani bir event işlenirken kod hatası oluşursa event kaybolur, sonsuza kadar yeniden denenmez. Bu bilinçli bir basitleştirme (dead-letter queue / retry mekanizması case kapsamında istenmiyor); prodüksiyon senaryosunda bir "poison message" kuyruğu eklenmesi önerilir.
