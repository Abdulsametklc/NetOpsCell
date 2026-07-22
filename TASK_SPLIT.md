# NetOpsCell — 3 Kişilik İş Bölümü ve Sprint Planı

Bu doküman [ARCHITECTURE.md](ARCHITECTURE.md)'deki teknik tasarımı **kim, hangi klasörde, hangi sırayla** yapacak sorusuna cevap verir. Amaç: üç kişi aynı anda, birbirinin dosyasına dokunmadan çalışabilsin; sık ve küçük merge'lerle entegrasyon riskini erkenden görebilelim.

---

## 0. MVP Tanımı — "kayıt→arama→sepet→ödeme" akışının NetOpsCell karşılığı

Case'de zaten tam olarak bunu karşılayan bir akış tanımlı: **Bölüm 11.3 Zorunlu Demo Senaryosu**. İlk hedefimiz, süsü olmadan, uçtan uca şunu çalıştırmak:

```
login (kayıt/giriş)
  → telemetri gönder (arama/keşif karşılığı: sistemin arızayı "bulması")
    → AI tahmini + otomatik saha ekibi ataması (sepet karşılığı: "işin" birine düşmesi)
      → saha teknisyeni çözüyor (COZULDU)
        → Gamification puan ekliyor, liderlik tablosuna yansıyor (ödeme/checkout karşılığı: "işlemin" tamamlanıp sonuç görünmesi)
```

Bu 5 adım çalışınca **canlı demoya çıkarılabilir bir MVP** elimizde olur. Buradan sonra kalan tüm zorunlu maddeler (state machine'in geri kalan durumları, SLA, mesajlaşma, rozetler, dashboard, güvenlik sertleştirme, audit log vb.) MVP'nin üzerine **eklenir**, hiçbiri atlanmaz — Bölüm 6'daki "Zorunlu Özellik Kapsama Tablosu" bunu garanti altına alır.

---

## 1. Modül Sahipliği (TAM AYRIK klasör sınırları)

| Kişi | Sahip Olduğu Klasör(ler) | Case Karşılığı |
|---|---|---|
| **Kişi 1** | `gateway/`, `services/identity-service/` | API Gateway + Identity Service (auth, kullanıcı, rol, audit, token) |
| **Kişi 2** | `services/incident-service/`, `services/ai-service/`, `services/gamification-service/` | Incident + AI + Gamification (arıza yaşam döngüsü, tahmin/atama, puan/rozet) |
| **Kişi 3** | `frontend/` | Tüm ekranlar (login, saha teknisyeni, NOC, süpervizör dashboard, liderlik/profil) |

**Neden Kişi 2'de 3 servis var, dengesiz değil mi?** Gamification Service çok küçüktür (sadece event dinleyici + birkaç GET, ~1-1.5 saat), bu yüzden gerçek iş yükü Kişi 1 ve Kişi 3 ile dengelenir. Aşağıdaki görev listelerinde saat tahminleri bunu gösteriyor (~6-8h her kişi). Ayrıca **T+1:00'dan itibaren Kişi 1, Identity+Gateway MVP'sini bitirir bitirmez Gamification Service'e; Kişi 3 de kendi ekranları bittikçe AI Service'in demo/UI tarafına** yardım eder (bkz. Bölüm 3, "yardım noktaları").

### 1.1 Ortak/Paylaşılan Dosyalar (dikkat — çakışma riski buradan çıkar)

Bu dosyalara **herkes** dokunur ama kural şu: **sadece kickoff'ta (T+0) birlikte taslak atılır, sonra küçük ve nadir PR'larla güncellenir**, uzun süre açık bırakılmaz:

| Dosya | Sahibi (koordinatör, ama içerik ortak) | Ne zaman donar |
|---|---|---|
| `docker-compose.yml` | Kişi 1 | T+1:00'da iskelet donar, sonrası küçük ekler |
| `.env.example` (kök + servis bazlı) | İlgili servis sahibi | Her servis kendi `.env.example`'ını kendi PR'ında ekler |
| `EVENTS.md` | Kişi 2 (event'leri o yayınlıyor) yazar, Kişi 1/3 event tüketirken okur | T+2:30'da ilk event şemaları donar |
| Ortak Pydantic sözleşmeleri (JWT payload şekli, `ResponseEnvelope`, Incident↔AI request/response şeması) | Kickoff'ta üçü birlikte belirler, `docs/CONTRACTS.md`'ye yazılır | **T+0:30'da donar** — bundan sonra değişirse mutlaka diğer ikisine haber verilir |
| Kök `README.md` | Herkes kendi bölümünü ekler | Sürekli açık, çakışma riski düşük (farklı bölümler) |

---

## 2. Git Branch Stratejisi

**Trunk-based, kısa ömürlü branch'ler.** Kişi başına tek dev branch açıp gün sonunda birleştirmek YASAK — o zaman dev merge cehennemi yaşanır. Onun yerine:

```
<isim>/<servis>-<özellik>
```

Örnekler:

| Kişi 1 | Kişi 2 | Kişi 3 |
|---|---|---|
| `ali/identity-register-otp` | `ayse/incident-crud-skeleton` | `mehmet/frontend-scaffold` |
| `ali/identity-jwt-rotation` | `ayse/incident-state-machine` | `mehmet/frontend-login` |
| `ali/gateway-routing` | `ayse/gamification-events` | `mehmet/frontend-teknisyen-dashboard` |
| `ali/gateway-jwt-middleware` | `ayse/ai-predict-fallback` | `mehmet/frontend-noc-dashboard` |
| `ali/gateway-rate-limit` | `ayse/ai-predict-llm` | `mehmet/frontend-supervizor-dashboard` |
| `ali/identity-audit-log` | `ayse/ai-assign-scoring` | `mehmet/frontend-leaderboard` |
| `ali/security-hardening` | `ayse/incident-sla-scheduler` | `mehmet/frontend-notifications-ws` |

(İsimleri gerçek isimlerinizle değiştirin.) Kural: bir branch **en fazla 1-1.5 saat** yaşar, sonra PR açılır → `main`'e merge edilir → branch silinir. Her PR küçük olduğu için review 5 dakikayı geçmemeli (hackathon'da karşılıklı 1 satır "LGTM" yeterli).

---

## 3. Checkpoint / Merge Takvimi (her 1-1.5 saatte bir)

> Not: Aşağıdaki saatler **göreceli** (T+0 = kod yazmaya başlama anı). Yarışmanın toplam süresine göre oranlayın; önemli olan **kadans** (1-1.5 saatte bir merge + smoke test), mutlak saat değil.

| Checkpoint | Zaman | Kişi 1 (Identity+Gateway) | Kişi 2 (Incident+AI+Game) | Kişi 3 (Frontend) | Merge Sonrası "Definition of Done" |
|---|---|---|---|---|---|
| **Kickoff** | T+0:00 → T+0:30 | `docs/CONTRACTS.md` taslağı (JWT payload, ResponseEnvelope, event şemaları) — üçü birlikte | aynı | aynı | Herkes aynı sözleşmeyi görüyor, `docker-compose.yml` iskeleti boş health-check'lerle ayakta |
| **CP1** | T+1:00 | Identity: register+login iskeleti (mock/basit JWT olsa da) | Incident CRUD iskeleti + Gamification skeleton (boş endpoint'ler) | Vite scaffold, routing, API client, `.env` | `docker compose up` ayakta, 3 parça birbirini bozmuyor |
| **CP2** | T+2:30 | Gerçek RS256 JWT + refresh rotation + rol claim'leri | Incident state machine (7 durum) + telemetry endpoint (AI'a stub cevap) | Login sayfası gerçek API'ye bağlı, teknisyen dashboard iskeleti | **Login uçtan uca çalışıyor** (frontend→gateway→identity→JWT) |
| **CP3** | T+4:00 | Gateway routing + rate limit + RBAC middleware + audit log | AI Service: `/predict` (önce rule-based fallback, sonra LLM) + Incident↔AI entegrasyonu | NOC ekranı iskeleti, telemetri gönderme formu | Login→telemetri→tahmin uçtan uca |
| **CP4 — 🎯 MVP HEDEFİ** | T+5:30 | İlk güvenlik geçişi (403 + audit doğrulama) | Atama algoritması + `PATCH status` (COZULDU'ya kadar) + `incident.resolved` event + Gamification puan ekleme | Liderlik tablosu sayfası + realtime toast | **Tam MVP canlı**: login→telemetri→AI tahmin+atama→teknisyen çözer→puan liderlik tablosuna yansır (case Bölüm 11.3 adım 1-6) |
| **CP5** | T+7:00 | Notification Hub (WS) + health aggregation | SLA scheduler, mesajlaşma thread, çözüm değerlendirme (yıldız), rozet tetikleme | SLA görselleri, mesajlaşma UI, rozet toast/modal | SLA sayaçları çalışıyor, rozetler tetikleniyor |
| **CP6** | T+8:30 | Bağımsızlık demo provası (`docker stop ai-service`) + güvenlik test provası (SQLi/IDOR/XSS manuel) | Kategori bazlı doğruluk kırılımı + manuel atama kuyruğu | Süpervizör dashboard grafikleri (Recharts) | Bağımsızlık senaryosu çalışıyor, dashboard dolu |
| **CP7** | T+10:00 | README (Identity+Gateway) | README (Incident+AI+Game) + `EVENTS.md` + `docs/ai-approach.md` | README (Frontend) | Tüm dokümantasyon tamam, Swagger kontrol edildi |
| **CP8 — Final** | T+11:00+ | — | — | — | Tam demo provası (case Bölüm 11.3 baştan sona), commit temizliği, son PR'lar |

**Her checkpoint'te 3 kişi de şunu yapar:** `git pull origin main` → kendi feature branch'ini rebase et → hızlıca `docker compose up` ile smoke test → yeni branch aç, devam et. Checkpoint'i kaçıran kişi bir sonrakinde iki katı entegrasyon riskiyle karşılaşır — bu yüzden checkpoint atlanmaz.

---

## 4. Kişi 1 — Görev Listesi (Identity Service + API Gateway)

- [ ] **(T0:30)** `docs/CONTRACTS.md`: JWT payload şeması, `ResponseEnvelope`, standart hata kodları — Kişi 2/3 ile birlikte
- [ ] **(CP1)** `identity-service` iskeleti: FastAPI app, SQLAlchemy modelleri (`users`, `refresh_tokens`, `otp_codes`, `audit_logs`), Alembic ilk migration
- [ ] **(CP1)** `POST /auth/register/customer`, `POST /auth/otp/verify` (sabit kod `1234`)
- [ ] **(CP1)** `POST /auth/personnel` (admin seed ile ilk admin kullanıcı)
- [ ] **(CP2)** `POST /auth/login` (personel: e-posta+şifre; müşteri: GSM+OTP), şifre politikası validasyonu + argon2 hash
- [ ] **(CP2)** RS256 access token (15dk) + refresh token rotation (7 gün, `replaced_by_token_id` zinciri) + reuse detection (tüm oturumları iptal)
- [ ] **(CP2)** Hesap kilitleme (5 başarısız giriş → 15dk, kalan süre response'da)
- [ ] **(CP3)** `gateway/`: routing tablosu (`/api/v1/auth/**` → Identity, vb.), JWT doğrulama middleware (public key ile, RS256), `X-User-*` header enjeksiyonu
- [ ] **(CP3)** Redis tabanlı rate limiting (login: IP başına 10/dk, genel: 100/dk)
- [ ] **(CP3)** `GET /auth/users`, `PATCH /auth/users/{id}` (rol/uzmanlık/bölge) → `identity.personnel.upserted` event yayınla
- [ ] **(CP3)** Audit log: `POST /internal/audit` (iç ağdan) + `GET /auth/audit-logs` (admin)
- [ ] **(CP4)** Rol/yetki matrisinin `Depends(require_roles([...]))` olarak her ilgili route'a uygulanması (kendi serviste + diğer 2 serviste de aynı deseni Kişi 2/3'e örnek olarak paylaş)
- [ ] **(CP5)** Notification Hub: `WS /api/v1/ws/notifications`, Redis Streams consumer, JWT'den `user_id`/`role` filtreleme
- [ ] **(CP5)** Gateway `/health` — tüm servislerin health durumunu agregasyon
- [ ] **(CP6)** Güvenlik provası: SQLi, IDOR, token manipülasyonu, XSS, brute-force senaryolarını **kendi sistemine karşı manuel dene**, bulduğun açığı kapat
- [ ] **(CP6)** `docker stop ai-service` / `docker stop gamification-service` ile bağımsızlık senaryosunu Kişi 2 ile birlikte prova et
- [ ] **(CP7)** `services/identity-service/README.md`, `gateway/README.md` (sorumluluk, endpoint listesi, env değişkenleri)
- [ ] **(Serbest kalınca / CP1 sonrası)** Kişi 2'ye Gamification Service'te yardım (event consumer iskeleti)

---

## 5. Kişi 2 — Görev Listesi (Incident + AI + Gamification)

- [ ] **(T0:30)** `docs/CONTRACTS.md`'ye Incident↔AI request/response şemaları + ilk event kataloğu taslağı ekle
- [ ] **(CP1)** `incident-service` iskeleti: modeller (`incidents`, `telemetry_readings`, `incident_status_history`, `incident_messages`, `incident_resolution_notes`, `incident_evaluations`), Alembic migration, `INC-YYYY-NNNNNN` sequence
- [ ] **(CP1)** `gamification-service` iskeleti: modeller (`point_ledger`, `user_stats`, `badges`, `user_badges`), Redis Streams consumer iskeleti (henüz event işlemeden)
- [ ] **(CP2)** Incident state machine (7 durum, geçiş tablosu, 422 kural dışı geçiş, 403 yetkisiz rol)
- [ ] **(CP2)** `POST /telemetry` — AI Service'e senkron çağrı (ilk aşamada AI Service henüz yoksa **sabit/stub** cevap ile test et, sonra gerçek servise bağlan), timeout+fallback (BELİRSİZ/ORTA + manuel kuyruk)
- [ ] **(CP3)** `ai-service` iskeleti: modeller (`predictions`, `accuracy_feedback`, `team_profile`, `team_workload`, `assignment_log`)
- [ ] **(CP3)** `POST /ai/predict` — **önce kural tabanlı fallback** (girdiye göre gerçekten değişen skor, ASLA sabit çıktı — diskalifiye riski!), eşik uygulaması (0.4/0.85) koda göm
- [ ] **(CP3)** `POST /ai/predict` — LLM entegrasyonu (Anthropic, forced tool-call, ARCHITECTURE.md Bölüm 8'deki prompt/şema), circuit breaker + retry
- [ ] **(CP4)** `POST /ai/assign` — skorlama algoritması (uzmanlık×0.4 + mesafe×0.3 + boşluk×0.3), Haversine mesafe, `team_profile`/`team_workload` cache'lerini `identity.personnel.upserted` ve `incident.*` event'lerinden güncelle
- [ ] **(CP4)** `PATCH /incidents/{id}/status` — COZULDU'ya kadar geçişler + çözüm notu zorunluluğu + `incident.resolved` event yayınla
- [ ] **(CP4)** Gamification: `incident.resolved` tüket → puan ekle (+10, hızlıysa +5), `user_stats` güncelle, ilk rozet kontrolü (İlk Müdahale)
- [ ] **(CP4)** `GET /game/leaderboard`, `GET /game/profile/{id}` — Frontend'in ihtiyacı olan minimum uçlar
- [ ] **(CP5)** SLA scheduler (arka plan görevi, 30sn periyodik, `sla_due_at` kontrolü, `incident.sla_breached` event)
- [ ] **(CP5)** `POST /incidents/{id}/messages` (thread), `POST /incidents/{id}/resolution-note`, `POST /incidents/{id}/evaluation` (1-5 yıldız, tek seferlik) → `incident.evaluated` event
- [ ] **(CP5)** Gamification: kalan rozetler (Hız Ustası, Kriz Yöneticisi, Uzman, Maratoncu), seviye hesaplama (Bronz/Gümüş/Altın/Platin), tekrar eden arıza cezası (-3)
- [ ] **(CP6)** `GET /ai/accuracy?breakdown=category` (kategori bazlı doğruluk kırılımı, bonus +3)
- [ ] **(CP6)** `GET /incidents/queue/unassigned`, `PATCH /incidents/{id}/assign` (manuel override), `GET /incidents/stats/summary` (dashboard agregasyonları)
- [ ] **(CP7)** `EVENTS.md` (tüm event'ler + örnek payload), `docs/ai-approach.md` (LLM yaklaşımı, prompt tasarımı, fallback stratejisi), 3 servisin README'leri
- [ ] **(CP7)** `docs/sample_telemetry.json` — min. 100 Türkçe örnek (seed + few-shot bağlamı için)

---

## 6. Kişi 3 — Görev Listesi (Frontend)

- [ ] **(T0:30)** `docs/CONTRACTS.md`'yi oku, API client katmanının tip tanımlarını (TypeScript interface'leri) sözleşmeye göre önceden yaz (backend henüz bitmeden **mock response** ile geliştirmeye başla — bloklanma!)
- [ ] **(CP1)** Vite + React + TS + Tailwind scaffold, routing (`react-router`), Zustand auth store, `axios`/`fetch` API client (base URL = Gateway), `.env`
- [ ] **(CP2)** Login sayfası (personel e-posta+şifre, müşteri GSM+OTP sekmesi), token saklama + otomatik refresh interceptor
- [ ] **(CP2)** Saha Teknisyeni Dashboard iskeleti: atanan arıza listesi (mock veri ile başla, CP3'te gerçek API'ye geç)
- [ ] **(CP3)** NOC Operatörü ekranı: tahmin listesi, "vaka aç"/"onayla" aksiyonu, telemetri simülatörü formu (kritik telemetri butonu — demo için önemli!)
- [ ] **(CP3)** Saha Teknisyeni ekranı gerçek API'ye bağlanıyor: durum güncelleme butonları (state machine'e göre sadece geçerli aksiyon gösterilir)
- [ ] **(CP4)** Liderlik tablosu sayfası (günlük/haftalık), profil ekranı (puan/seviye/rozet/istatistik)
- [ ] **(CP4)** Çözüm notu formu + "vakayı çöz" akışı, temel loading/error/empty state'ler
- [ ] **(CP5)** WebSocket bağlantısı (Notification Hub) — rozet kazanma toast/modal, yeni atama bildirimi
- [ ] **(CP5)** Vaka içi mesajlaşma (thread) UI, SLA kalan süre göstergesi (renk kodlu: kırmızı/turuncu/uyarı)
- [ ] **(CP6)** Süpervizör Dashboard: 6 zorunlu bileşen (arıza dağılımı, öncelik dağılımı+trend, SLA uyum oranı, AI doğruluk metriği, saha ekibi performansı, bekleyen atama kuyruğu) — Recharts ile
- [ ] **(CP6)** Manuel atama aksiyonu (süpervizör kuyruktan ekip seçip atar)
- [ ] **(CP6)** Admin panel: personel hesabı oluşturma formu, audit log görüntüleme tablosu
- [ ] **(CP6)** Responsive kontrol (mobil/tablet breakpoint'leri), tüm ekranlarda loading/error/empty state tutarlılığı
- [ ] **(CP7)** `frontend/README.md`
- [ ] **(Serbest kalınca)** AI Service demo ekranına (tahmin sonucu + "neden bu ekip seçildi" açıklaması gösterimi) katkı, Kişi 2 ile birlikte

---

## 7. Zorunlu Özellik Kapsama Tablosu (hiçbir şey atlanmasın diye)

| Case Maddesi | Sahibi | Hangi Checkpoint'e kadar bitmeli |
|---|---|---|
| GSM+OTP kayıt, personel admin kaydı | Kişi 1 | CP1 |
| Şifre politikası + hata mesajı, argon2 hash | Kişi 1 | CP2 |
| Hesap kilitleme (5/15dk) | Kişi 1 | CP2 |
| JWT (15dk) + refresh (7g) + rotation + theft detection | Kişi 1 | CP2 |
| Rol/yetki matrisi (endpoint seviyesinde, 403) | Kişi 1 (Identity+Gateway) + Kişi 2/3 (kendi endpoint'lerinde uygular) | CP4 |
| Audit log (6 olay tipi) | Kişi 1 | CP3 |
| Telemetri girişi + AI çağrısı + AI kapalıyken BELİRSİZ/ORTA fallback | Kişi 2 | CP2-CP3 |
| Arıza numarası (INC-YYYY-NNNNNN) | Kişi 2 | CP1 |
| State machine (7 durum, 422/403) | Kişi 2 | CP2 |
| Arıza türleri + öncelik atama (AI, override) | Kişi 2 | CP3-CP4 |
| SLA kuralları (4 seviye, sayaç, aşım işareti) | Kişi 2 | CP5 |
| Saha iletişimi (thread mesajlaşma) | Kişi 2 (API) + Kişi 3 (UI) | CP5 |
| Çözüm değerlendirmesi (1-5 yıldız, tek seferlik) | Kişi 2 | CP5 |
| AI Görev 1: arıza tahmini (olasılık + öneri eşikleri) | Kişi 2 | CP3 |
| AI Görev 2: arıza türü sınıflandırma | Kişi 2 | CP3 |
| AI Görev 3: skorlama tabanlı akıllı atama | Kişi 2 | CP4 |
| AI doğruluk takibi (+ kategori kırılımı bonusu) | Kişi 2 | CP4 / CP6 |
| Puan tablosu (COZULDU, hızlı müdahale, kalıcı çözüm, SLA aşımı, tekrar arıza) | Kişi 2 | CP4-CP5 |
| Rozetler (6 adet) | Kişi 2 | CP5 |
| Seviye sistemi (4 seviye) | Kişi 2 | CP4 |
| Liderlik tablosu (günlük/haftalık) + profil | Kişi 2 (API) + Kişi 3 (UI) | CP4 |
| Süpervizör Dashboard (6 bileşen) | Kişi 3 (UI) + Kişi 2 (agregasyon API) | CP6 |
| API Gateway (routing, rate limit, JWT) | Kişi 1 | CP3 |
| Event tabanlı mimari (Redis) | Kişi 2 (yayıncı) + Kişi 1/3 (tüketici: notification hub) | CP3-CP5 |
| Güvenlik sertleştirme (SQLi/IDOR/token/XSS/brute-force) | Kişi 1 (koordinatör) + herkes kendi servisinde | CP6 |
| Bağımsızlık demo (`docker stop`) | Kişi 1 + Kişi 2 birlikte prova | CP6 |
| Docker Compose (tek komut) | Kişi 1 | CP1 (iskelet) → CP7 (final) |
| README'ler (ana + servis başına) | Herkes kendi modülü | CP7 |
| `EVENTS.md` | Kişi 2 | CP7 |
| `docs/ai-approach.md` | Kişi 2 | CP7 |
| Swagger/OpenAPI (en az Incident+AI) | Otomatik (FastAPI) — Kişi 2 kontrol eder | CP7 |
| Unit/integration testler | Herkes kendi modülünde, zaman kalırsa CP6-CP7 arası | CP7 |
| CI/CD (bonus +2) | Kişi 1 (zaman kalırsa) | CP7 sonrası, opsiyonel |

---

## 8. Pratik Kurallar

1. **Kimse `main`'e doğrudan push atmaz** — her değişiklik küçük bir PR ile gelir, karşı taraf 2 dakikada göz atar, merge edilir.
2. **Bir checkpoint'te kendi görevini bitiremediysen** — bir sonraki checkpoint'e "borç" olarak taşınır ama mutlaka söylenir; sessizce ertelenmez (özellikle Identity/JWT gecikirse Kişi 2/3 bloklanır).
3. **Contract değişikliği (`docs/CONTRACTS.md`)** T+0:30'dan sonra yapılacaksa, değiştiren kişi diğer ikisine **hemen** haber verir (Slack/WhatsApp mesajı yeterli, toplantı gerekmez).
4. **Demo provası** en geç CP6'dan itibaren her checkpoint sonunda 5 dakika ayrılır: case Bölüm 11.3'teki 8 adımı baştan sona dene, neyin eksik olduğunu gör.
