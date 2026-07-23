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

## Model Performansı

Fallback modeli, LLM sağlayıcısına ulaşılamadığında kullanılan gerçek bir SVM sınıflandırıcısıdır. Eğitim verisi 122 etiketli telemetri örneğinden oluşur; model seçimi öncesinde 25 örneklik holdout ayrılmış, adaylar kalan 97 örnekte GridSearchCV ve 5-fold stratified cross-validation ile karşılaştırılmıştır.

![NetOpsCell AI model performansı](docs/model-performance.svg)

### Algoritma Karşılaştırması

Model seçiminde kullanılan ana kriter macro F1 skorudur. Aşağıdaki grafik, yalnızca model seçim havuzundaki (97 örnek) sızıntısız CV sonuçlarını gösterir.

```mermaid
xychart-beta
	title "5-fold CV macro F1 karşılaştırması"
	x-axis [SVM, LogisticRegression, RandomForest, GradientBoosting]
	y-axis "Macro F1" 0 --> 1
	bar [0.856, 0.845, 0.817, 0.796]
```

| Algoritma | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | Durum |
|---|---:|---:|---:|---:|---|
| **SVM (RBF)** | **0.906** | **0.881** | **0.861** | **0.856** | **Seçildi** |
| LogisticRegression | 0.895 | 0.873 | 0.850 | 0.845 | Aday |
| RandomForest | 0.886 | 0.838 | 0.828 | 0.817 | Aday |
| GradientBoosting | 0.865 | 0.815 | 0.806 | 0.796 | Aday |

Seçilen SVM için hiperparametreler `C=1.0` ve `gamma=1.0`'dır. Bu sonuçlar holdout performansı değil, model seçimi havuzundaki 5-fold CV ortalamalarıdır.

### Holdout ve Kategori Bazlı Sonuçlar

Model seçimi tamamlandıktan sonra hiç görülmemiş 25 örneklik holdout üzerinde tek seferlik değerlendirme yapılmıştır. Genel doğruluk **0.88 (%88)**, macro F1 ise **0.86** olmuştur.

```mermaid
xychart-beta
	title "SVM holdout macro F1 - kategori bazında"
	x-axis [BAGLANTI, BELIRSIZ, DONANIM, GUC_KESINTISI, ISINMA, YAZILIM]
	y-axis "F1" 0 --> 1
	bar [0.89, 0.92, 1.00, 0.89, 0.80, 0.67]
```

```mermaid
pie showData
	title "Eğitim verisi sınıf dağılımı (122 örnek)"
	"BELIRSIZ" : 30
	"BAGLANTI" : 22
	"GUC_KESINTISI" : 22
	"ISINMA" : 22
	"DONANIM" : 16
	"YAZILIM" : 10
```

| Ölçüm | Sonuç | Veri / bağlam |
|---|---:|---|
| Eğitim verisi | 122 örnek | 6 arıza sınıfı |
| Model seçim havuzu | 97 örnek | 5-fold stratified CV |
| Ayrı holdout | 25 örnek | Model seçimi dışında tutuldu |
| Holdout doğruluğu | **%88** | Seçilen SVM |
| Holdout macro precision | %91 | Seçilen SVM |
| Holdout macro recall | %85 | Seçilen SVM |
| Holdout macro F1 | %86 | Seçilen SVM |
| Sentetik senaryo doğruluğu | **%83.3** | Eğitimde görülmeyen 12 net senaryo |

### Tahmin Fallback Akışı

```mermaid
flowchart LR
	INPUT[Telemetri] --> LLM{LLM erişilebilir mi?}
	LLM -->|Evet| CLAUDE[Claude forced tool-call]
	LLM -->|Hayır / timeout| SVM[SVM ML fallback]
	CLAUDE --> RESULT[probability + fault_type]
	SVM --> RESULT
	RESULT --> RULES[Deterministik eşikler]
	RULES --> OUTPUT[suggestion + priority]
	SVM -. model.joblib eksik .-> RULE[Son çare: kural fallback]
	RULE --> RESULT
```

Grafiklerdeki CV, holdout ve sentetik test sonuçlarının ayrıntılı metodolojisi için [`docs/ml-model.md`](../../docs/ml-model.md) dosyasına; LLM ve dayanıklılık kararları için [`docs/ai-approach.md`](../../docs/ai-approach.md) dosyasına bakılabilir. Veri setinin küçük olması ve `YAZILIM` sınıfındaki düşük holdout F1 değeri nedeniyle bu sonuçlar üretim kalitesi garantisi değil, mevcut veriyle yapılan doğrulama olarak değerlendirilmelidir.

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
