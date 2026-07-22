# NetOpsCell — Servisler Arası Sözleşmeler (CONTRACTS.md)

Bu dosya kod yazılabilir netlikte bir **sözleşme** dokümanıdır — mimari kararların gerekçesi için [ARCHITECTURE.md](../ARCHITECTURE.md)'ye bakın, burada sadece **tam olarak hangi alan, hangi tip, zorunlu mu** sorularının cevabı var. Amaç: Kişi 1/3, ilgili servisin tüm kodunu okumadan doğrudan bu şemalara göre entegrasyon kodu yazabilsin.

**Kapsam (bu ilk taslak):** Incident ↔ AI Service istek/cevap şemaları + servisler arası event kataloğu. JWT payload / `ResponseEnvelope` gibi ortak altyapı şemaları kickoff'ta üç kişi birlikte ekleyecek (TASK_SPLIT.md §1.1).

**Değişiklik kuralı:** Bu dosya donduktan sonra (ilk taslak merge edildikten sonra) değiştirecek kişi, TASK_SPLIT.md §8/§9 gereği diğer iki kişiye **hemen** haber vermek zorunda — burada tanımlı bir şemayı sessizce değiştirmek diğer ikisinin kodunu kırar.

Her servis bu tipleri kendi `app/schemas/contracts.py` dosyasına **kopyalar** (database-per-service kuralı gibi, ortak bir pip paketi yok — hackathon kapsamında en basit çözüm budur). Bu dosya "kaynak" (source of truth), her serviste birebir aynı kopyası bulunur.

---

## 1. Ortak Enum'lar

AI ve Incident şemalarının ikisinin de ihtiyaç duyduğu, tek yerden kopyalanacak sabitler:

```python
from enum import Enum

class FaultType(str, Enum):
    DONANIM = "DONANIM"
    GUC_KESINTISI = "GUC_KESINTISI"
    BAGLANTI = "BAGLANTI"
    YAZILIM = "YAZILIM"
    ISINMA = "ISINMA"
    BELIRSIZ = "BELIRSIZ"

class Priority(str, Enum):
    DUSUK = "DUSUK"
    ORTA = "ORTA"
    YUKSEK = "YUKSEK"
    KRITIK = "KRITIK"

class Suggestion(str, Enum):
    IZLE = "IZLE"
    VAKA_AC = "VAKA_AC"
    ACIL = "ACIL"

class IncidentStatus(str, Enum):
    YENI = "YENI"
    ATANDI = "ATANDI"
    YOLDA = "YOLDA"
    MUDAHALE_EDILIYOR = "MUDAHALE_EDILIYOR"
    PARCA_BEKLENIYOR = "PARCA_BEKLENIYOR"
    COZULDU = "COZULDU"
    KAPANDI = "KAPANDI"

class PowerStatus(str, Enum):
    NORMAL = "NORMAL"
    KESINTIDE = "KESINTIDE"

class PredictionMethod(str, Enum):
    LLM = "LLM"
    RULE_FALLBACK = "RULE_FALLBACK"
```

---

## 2. Incident Service → AI Service Sözleşmeleri

### 2.1 `POST /api/v1/telemetry` — İstemci → Incident Service

Bu, Incident Service'in dışa açtığı giriş noktası; `PredictRequest` ile birebir aynı şemadır (Incident Service, bu body'yi olduğu gibi AI Service'e ileterek `/ai/predict`'i çağırır).

```python
from pydantic import BaseModel, Field

class TelemetryInput(BaseModel):
    station_code: str
    lat: float
    lng: float
    signal_strength: float                       # dBm, genelde negatif (örn. -105)
    packet_loss: float = Field(ge=0, le=100)      # yüzde
    temperature: float                            # santigrat
    power_status: PowerStatus
    recent_fault_count: int = 0                   # son 24 saatte aynı istasyonda kaç arıza kaydı var
```

### 2.2 `POST /api/v1/ai/predict` — Incident Service → AI Service (senkron)

**Request:** `TelemetryInput` ile aynı şema (`PredictRequest = TelemetryInput`).

**Response — 200 OK:** Aşağıdaki `PredictResponse`, sistem genelindeki standart `{success, data, error}` zarfının **`data`** alanının içeriğidir (zarfın kendisi değil) — yani gerçek HTTP body'si `{"success": true, "data": {...PredictResponse alanları...}, "error": null}` şeklindedir. Tüketen taraf önce zarfı açıp `data` alanını `PredictResponse`'a validate etmelidir.

```python
class PredictResponse(BaseModel):
    probability: float = Field(ge=0.0, le=1.0)
    fault_type: FaultType
    priority: Priority
    suggestion: Suggestion
    method: PredictionMethod          # "LLM" ya da "RULE_FALLBACK" — hangi yol devrede olduğunun şeffaflığı
    confidence_explanation: str       # LLM'in/kuralın kısa gerekçesi (Türkçe, 1-2 cümle)
```

**Hata / dayanıklılık davranışı (Incident Service'in bilmesi gereken):**

| Durum | AI Service Davranışı | Incident Service'in Yapması Gereken |
|---|---|---|
| LLM sağlayıcısı zaman aşımı/hata | İçeride otomatik `RULE_FALLBACK`'e düşer, yine `200 OK` + geçerli `PredictResponse` döner | Hiçbir şey — cevap her koşulda gelir |
| AI Service'in kendisi ulaşılamıyor (bağlantı hatası / 2sn timeout) | — | `fault_type=BELIRSIZ`, `priority=ORTA` ile vaka oluştur, manuel atama kuyruğuna ekle |
| Geçersiz istek gövdesi | `422` + `ResponseEnvelope` hata şekli | Telemetri girdisini loglayıp isteği reddet (bu normalde hiç olmamalı, Incident Service kendi tarafında da aynı Pydantic modeliyle doğrular) |

### 2.3 `POST /api/v1/ai/assign` — Incident Service → AI Service (senkron, vaka oluşturulduktan sonra)

**Request:**

```python
class AssignRequest(BaseModel):
    incident_id: str          # uuid
    incident_number: str      # "INC-2026-000123"
    fault_type: FaultType
    priority: Priority
    lat: float
    lng: float
```

**Response — 200 OK:**

```python
class ScoreComponents(BaseModel):
    uzmanlik_eslesme: float   # 0 veya 1
    mesafe_yakinlik: float    # 0.0 - 1.0
    bosluk_orani: float       # 0.0 - 1.0 (negatif olabilir teorik olarak, ama pratikte 0'a clamp edilir)

class AssignResponse(BaseModel):
    queued: bool                              # true ise aşağıdaki alanlar None, vaka kapasite kuyruğunda
    team_id: str | None = None
    team_name: str | None = None
    score: float | None = None
    components: ScoreComponents | None = None
```

`queued=true` döndüğünde Incident Service: `assigned_team_id=null`, durum `YENI` kalır, vaka `GET /incidents/queue/unassigned`'da görünür hale gelir.

---

## 3. Event Kataloğu — Taslak (Redis Streams üzerinden)

**Stream topolojisi:** Her event tipi kendi Redis Stream'inde yayınlanır (`XADD <event_type> ...`), stream key'i doğrudan `event_type` string'idir (örn. `XADD incident.resolved * ...`). Her tüketici servis kendi servis adını consumer group adı olarak kullanır (`XGROUP CREATE incident.resolved gamification-service ...`) — böylece bir servis kapalıyken kaçırdığı event'leri tekrar ayağa kalktığında `XREADGROUP` ile okumaya devam eder.

Aşağıdaki modellerin hepsinde `event_type` alanı sabit bir `Literal` — deserialize ederken hangi event geldiğini ayırt etmek için kullanılır.

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class IdentityPersonnelUpserted(BaseModel):
    event_type: Literal["identity.personnel.upserted"] = "identity.personnel.upserted"
    user_id: str
    name: str
    specializations: list[FaultType]
    regions: list[str]
    base_lat: float
    base_lon: float
    is_active: bool

class AiPredictionCompleted(BaseModel):
    event_type: Literal["ai.prediction.completed"] = "ai.prediction.completed"
    telemetry_id: str
    probability: float
    fault_type: FaultType
    priority: Priority
    suggestion: Suggestion
    method: PredictionMethod

class IncidentCreated(BaseModel):
    event_type: Literal["incident.created"] = "incident.created"
    incident_id: str
    incident_number: str
    station_code: str
    fault_type: FaultType
    priority: Priority
    probability: float
    created_at: datetime

# CP4: incident-service ve ai-service arasinda uygulandi (asagidaki tanim ile birebir).
class IncidentAssigned(BaseModel):
    event_type: Literal["incident.assigned"] = "incident.assigned"
    incident_id: str
    team_id: str
    team_name: str
    score: float
    assigned_by: str            # "SYSTEM" ya da bir user_id (süpervizör manuel atadıysa)
    assigned_at: datetime

class IncidentStatusChanged(BaseModel):
    event_type: Literal["incident.status_changed"] = "incident.status_changed"
    incident_id: str
    from_status: IncidentStatus
    to_status: IncidentStatus
    changed_by: str
    changed_at: datetime

class IncidentTypeChanged(BaseModel):
    event_type: Literal["incident.type_changed"] = "incident.type_changed"
    incident_id: str
    original_fault_type: FaultType
    new_fault_type: FaultType
    changed_by: str
    changed_at: datetime

class IncidentPriorityChanged(BaseModel):
    event_type: Literal["incident.priority_changed"] = "incident.priority_changed"
    incident_id: str
    original_priority: Priority
    new_priority: Priority
    changed_by: str
    changed_at: datetime

class IncidentPartFulfilled(BaseModel):
    event_type: Literal["incident.part.fulfilled"] = "incident.part.fulfilled"
    incident_id: str
    fulfilled_by: str
    fulfilled_at: datetime

class IncidentSlaBreached(BaseModel):
    event_type: Literal["incident.sla_breached"] = "incident.sla_breached"
    incident_id: str
    priority: Priority
    sla_due_at: datetime
    breached_at: datetime

class IncidentResolved(BaseModel):
    event_type: Literal["incident.resolved"] = "incident.resolved"
    incident_id: str
    team_id: str
    fault_type: FaultType
    priority: Priority
    created_at: datetime
    resolved_at: datetime

class IncidentEvaluated(BaseModel):
    event_type: Literal["incident.evaluated"] = "incident.evaluated"
    incident_id: str
    stars: int = Field(ge=1, le=5)
    is_permanent: bool
    evaluated_by: str

class GamePointsAwarded(BaseModel):
    event_type: Literal["game.points_awarded"] = "game.points_awarded"
    user_id: str
    incident_id: str | None
    points: int
    reason: str
    new_total: int

class BadgeEarned(BaseModel):
    event_type: Literal["badge.earned"] = "badge.earned"
    user_id: str
    badge_code: str
    earned_at: datetime
```

### 3.1 Yayıncı / Tüketici Hızlı Referans

| Event | Yayınlayan | Tüketen |
|---|---|---|
| `identity.personnel.upserted` | Identity (Kişi 1) | AI (`team_profile` cache) |
| `ai.prediction.completed` | AI (Kişi 2) | — (opsiyonel analitik) |
| `incident.created` | Incident (Kişi 2) | Gamification (tekrar arıza tespiti) |
| `incident.assigned` | Incident (Kişi 2) | AI (`team_workload` cache), Notification Hub |
| `incident.status_changed` | Incident (Kişi 2) | AI (`team_workload` cache) |
| `incident.type_changed` | Incident (Kişi 2) | AI (doğruluk takibi) |
| `incident.priority_changed` | Incident (Kişi 2) | — |
| `incident.part.fulfilled` | Incident (Kişi 2) | — |
| `incident.sla_breached` | Incident (Kişi 2, scheduler) | Gamification (-3 ceza), Notification Hub |
| `incident.resolved` | Incident (Kişi 2) | Gamification, AI (`team_workload` cache) |
| `incident.evaluated` | Incident (Kişi 2) | Gamification (+15 kalıcı çözüm) |
| `game.points_awarded` | Gamification (Kişi 2) | Notification Hub |
| `badge.earned` | Gamification (Kişi 2) | Notification Hub |

---

## 4. Ortak Altyapı Şemaları (ARCHITECTURE.md §3.2 / §5.1'deki kararların birebir aktarımı)

> Not: Bu bölümdeki şemalar Identity Service + Gateway'i ilgilendirir (Kişi 1); burada yeni bir tasarım kararı alınmadı, sadece ARCHITECTURE.md'de zaten karara bağlanmış şekiller kod-yazılabilir netliğe taşındı. Kişi 1, kendi implementasyonunda bir sapma gerekirse bu bölümü güncelleyip diğer ikisine haber vermeli (TASK_SPLIT.md §8).

### 4.1 `ResponseEnvelope` — tüm servislerin tüm response'larında ortak zarf

```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class ErrorDetail(BaseModel):
    code: str                      # bkz. 4.3 Standart Hata Kodları
    message: str
    violations: list[str] | None = None      # örn. WEAK_PASSWORD'de hangi kurallar ihlal edildi
    retry_after_seconds: int | None = None    # örn. ACCOUNT_LOCKED / RATE_LIMITED

class ResponseEnvelope(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ErrorDetail | None = None
```

Örnek başarı: `{"success": true, "data": {...}, "error": null}`
Örnek hata: `{"success": false, "data": null, "error": {"code": "INVALID_TRANSITION", "message": "YENI durumundan MUDAHALE_EDILIYOR'a doğrudan geçiş yapılamaz", "violations": null, "retry_after_seconds": null}}`

### 4.2 JWT Access Token Payload

```python
from pydantic import BaseModel

class JWTPayload(BaseModel):
    sub: str                       # user_id (uuid)
    role: str                      # MUSTERI | SAHA_TEKNISYENI | NOC_OPERATORU | SUPERVIZOR | ADMIN
    specializations: list[str] = []   # sadece SAHA_TEKNISYENI için anlamlı
    regions: list[str] = []
    token_type: str = "access"
    iat: int
    exp: int
```

- İmza algoritması: **RS256**. Gateway ve servisler Identity'nin **public key**'i ile doğrular, private key'e ihtiyaç duymaz.
- Doğrulanan claim'ler downstream servislere `X-User-Id`, `X-User-Role`, `X-User-Specializations`, `X-User-Regions` header'ları olarak Gateway tarafından enjekte edilir (ARCHITECTURE.md §5, madde 2). Her servis kendi içinde de rol kontrolü yapar (defense in depth) — Gateway header'larına körü körüne güvenilmez.
- Access token ömrü: 15 dakika. Refresh token (opaque, JWT değil) ömrü: 7 gün, rotation zinciriyle (`replaced_by_token_id`).

### 4.3 Standart Hata Kodları

| Kod | HTTP Status | Kullanıldığı Yer |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Genel Pydantic doğrulama hatası (alan tipi/uzunluk vb.) |
| `WEAK_PASSWORD` | 422 | Şifre politikası ihlali — `violations` alanında hangi kural(lar) |
| `INVALID_CREDENTIALS` | 401 | Login: yanlış e-posta/şifre ya da GSM/OTP |
| `ACCOUNT_LOCKED` | 423 | 5 başarısız girişten sonra — `retry_after_seconds` dolu |
| `TOKEN_EXPIRED` | 401 | `exp` geçmiş access/refresh token |
| `TOKEN_INVALID` | 401 | İmza doğrulanamayan / `alg=none` / bozuk token |
| `TOKEN_REUSE_DETECTED` | 401 | Zaten `revoked_at` dolu refresh token tekrar kullanılmaya çalışıldı — tüm oturumlar iptal edilir |
| `FORBIDDEN` | 403 | Rol yetersiz (RBAC) — audit log'a `UNAUTHORIZED_ACCESS` olarak yazılır |
| `NOT_FOUND` | 404 | Kaynak yok / IDOR koruması (sahiplik kontrolünde de aynı kod döner — kaynağın var olup olmadığı sızdırılmaz) |
| `INVALID_TRANSITION` | 422 | Incident state machine'de graf dışı geçiş — `{"from": "...", "to": "..."}` detayında |
| `RATE_LIMITED` | 429 | Gateway rate limit aşımı |
| `AI_SERVICE_UNAVAILABLE` | — (Incident bunu asla dışa döndürmez) | Incident Service içi durum; dış cevap her zaman `BELIRSIZ/ORTA` ile 201 döner, bkz. Bölüm 2.2 |
