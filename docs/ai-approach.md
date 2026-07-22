# NetOpsCell — AI Yaklaşım Dokümanı

Case Bölüm 5, üç yaklaşımdan birini serbest bırakıyor: (a) klasik ML, (b) kural+ML hibrit, (c) LLM API entegrasyonu. Bu projede **(c) LLM API entegrasyonu + deterministik kural tabanlı fallback** seçildi. Bu doküman neyi, neden, nasıl yaptığımızı ve gerçekte test edip edemediğimizi anlatır.

## 1. Neden LLM, Bilinçli Trade-off

Kendi eğittiğimiz bir ML modeli (scikit-learn vb.) bonus +8 puan getiriyor (case §12.1); LLM yaklaşımı bu bonusu hedeflemiyor. Bunun yerine:

- **Hız:** Etiketli veri toplama + model eğitimi + değerlendirme döngüsü olmadan, prompt mühendisliğiyle makul kalitede bir sınıflandırıcı hızlıca elde edilir — hackathon zaman kısıtında değerli.
- **Esneklik:** Telemetri paternleri genişletildiğinde (yeni arıza türü, yeni sinyal kombinasyonu) yeniden eğitim gerekmeden prompt/few-shot örnekleri güncellenir.
- **Açıklanabilirlik:** LLM her tahminle birlikte kısa bir gerekçe (`confidence_explanation`) üretir — jüri demo'sunda "neden bu tahmin?" sorusuna doğrudan cevap.

Karşılığında hedeflenen bonuslar: mesaj kuyruğu (+5, Redis Streams — bkz. EVENTS.md), kategori bazlı doğruluk kırılımı (+3, `GET /ai/accuracy?breakdown=category`), gerçek zamanlı bildirim (+2, henüz Gateway'de kurulmadı).

## 2. Mimari İlke: LLM Sadece Fuzzy Kısımda

En kritik tasarım kararı: **LLM'in çıktısı sadece iki fuzzy değer** — `probability` (0.0-1.0) ve `fault_type`. Bunun ötesindeki her şey (eşik bucket'ları, öncelik, atama algoritması) **deterministik Python kodunda**, LLM'e hiç danışılmadan hesaplanır.

Sebep: Case'in eşikleri kesin ("0.40 altı IZLE, 0.85 üstü ACIL" — §5.1). Bu eşikleri LLM'e bırakmak, aynı girdiye jüri her sorduğunda LLM'in ürettiği rastgele varyasyonun iş kuralına sızmasına yol açardı. Onun yerine LLM sadece "bu telemetri ne kadar arızalı görünüyor ve hangi türe benziyor" sorusuna cevap verir; geri kalanı kod garanti eder.

```
LLM/Kural  →  probability (float), fault_type (enum)
                    │
                    ▼
        thresholds.py (deterministik)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  suggestion (IZLE/           priority (DUSUK/ORTA/
  VAKA_AC/ACIL)                YUKSEK/KRITIK)
```

Kaynak: `services/ai-service/app/core/thresholds.py`.

## 3. Görev 1+2 — Tahmin + Sınıflandırma (Tek LLM Çağrısında Birleşik)

**Model:** Anthropic `claude-sonnet-5`, `temperature=0` (tutarlılık için).

**Yöntem:** Serbest metin çıktısını parse etmek yerine **forced tool use** — model, `emit_diagnosis` adlı bir tool'u zorunlu çağırmak durumunda bırakılır (`tool_choice={"type": "tool", "name": "emit_diagnosis"}`). Bu, LLM'in yanlış formatlı JSON döndürme riskini sıfırlar; çıktı doğrudan Pydantic ile doğrulanabilir.

```python
DIAGNOSIS_TOOL = {
    "name": "emit_diagnosis",
    "input_schema": {
        "type": "object",
        "properties": {
            "probability": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "fault_type": {"type": "string", "enum": ["DONANIM", "GUC_KESINTISI", "BAGLANTI", "YAZILIM", "ISINMA", "BELIRSIZ"]},
            "rationale": {"type": "string"},
        },
        "required": ["probability", "fault_type", "rationale"],
    },
}
```

**Prompt tasarımı:** Sistem prompt'u modeli "Turkcell şebeke altyapısında uzman bir arıza teşhis asistanı" olarak konumlandırır, 6 kategoriyi tanımlar ve 3 few-shot örnek içerir (normal, ısınma, güç kesintisi senaryoları). Telemetri sayısal verisi, önce Türkçe doğal dil cümlesine çevrilir (`telemetry_to_text()`):

```
"İstasyon IST-1000: sinyal gücü -95 dBm, paket kaybı %25, sıcaklık 80°C,
güç durumu: NORMAL, son 24 saatte geçmiş arıza sayısı: 0."
```

Tam prompt ve tool şeması: `services/ai-service/app/core/llm_client.py`.

## 4. Görev 3 — Akıllı Saha Ekibi Ataması (LLM Değil, Deterministik)

Atama algoritması **LLM'e hiç danışmaz** — case'in verdiği formülün doğrudan koda dökülmüş hali:

```
skor = (uzmanlık_eşleşme × 0.4) + (mesafe_yakınlık × 0.3) + (boşluk_oranı × 0.3)
```

- `uzmanlık_eşleşme`: ekibin uzmanlık listesi arızanın türünü içeriyorsa 1, değilse 0
- `mesafe_yakınlık`: Haversine mesafesi, 50km normalizasyon yarıçapıyla `max(0, 1 - km/50)`
- `boşluk_oranı`: `1 - (aktif_arıza/kapasite)`, kapasite sabit 5

Bu bilinçli bir ayrım: atama tamamen açıklanabilir, tekrarlanabilir ve jüri "neden bu ekip?" diye sorduğunda `assignment_log` tablosundaki (tüm adayların skorları saklı) kayıttan birebir cevaplanabilir. Kaynak: `services/ai-service/app/core/assignment.py`, `app/core/geo.py`.

## 5. Dayanıklılık — LLM Sağlayıcısı da Çökebilir

AI Service'in kendisi ayaktayken bile dış LLM API'si (ağ sorunu, rate limit, geçici kesinti) yanıt vermeyebilir. Bu durumda **asla sabit/mock bir çıktı dönülmez** — case'in diskalifiye kuralı ("AI servisi mock/hardcoded ise değerlendirme dışı") burada özellikle önemli, çünkü fallback yolu da gerçek bir algoritma:

```python
# rule_fallback.py — girdiye göre GERÇEKTEN değişir
if temperature > 65:        contributions[ISINMA] += 0.35
if packet_loss > 15:        contributions[BAGLANTI] += 0.30
if signal_strength < -100:  contributions[BAGLANTI] += 0.20
if power_status == KESINTIDE: contributions[GUC_KESINTISI] += 0.35
if recent_fault_count >= 2: contributions[DONANIM] += 0.15
```

**Devreye girme sırası:**
1. `ANTHROPIC_API_KEY` tanımlı değilse → doğrudan fallback (senkron, network çağrısı bile yapılmaz)
2. LLM çağrısı 4sn'de yanıt vermezse veya hata verirse → 1 retry
3. Retry de başarısız olursa → fallback + **circuit breaker**: art arda 3 başarısızlık sonrası 30sn'lik sogutma penceresinde LLM hiç denenmez, doğrudan fallback kullanılır (dış API'yi gereksiz yormamak için)

Her `predictions` kaydında `method` alanı (`LLM` / `RULE_FALLBACK`) saklanır — hangi yolun devrede olduğu her zaman şeffaf.

**Kritik ayrım:** Bu, case'in "AI Service kapalıyken arıza BELİRSİZ işaretlenir" kuralından (bkz. ARCHITECTURE.md §4.2) farklı bir katman. O kural **Incident Service'in AI Service'e hiç ulaşamaması** durumudur (bağımsızlık demo'su, `docker stop ai-service`). Buradaki fallback ise **AI Service ayaktayken sadece dış LLM sağlayıcısına ulaşamaması** durumudur — ayrı bir dayanıklılık katmanı.

## 6. Doğruluk Takibi

NOC Operatörü veya Süpervizör bir tahminin `fault_type`'ını `PATCH /incidents/{id}/fault-type` ile değiştirirse, Incident Service `incident.type_changed` event'i yayınlar; AI Service bunu `accuracy_feedback` tablosuna `is_correct=false` olarak kaydeder. Değiştirilmeyen tahminler zımnen doğru sayılır.

`GET /ai/accuracy?breakdown=category` — genel oran + kategori bazlı kırılım (bonus +3). `predictions` tablosu (tüm tahminler) ile `accuracy_feedback` tablosu (sadece düzeltilenler) arasında doğrudan foreign key yok (farklı anlarda, birbirinden bağımsız yazılırlar); bu yüzden karşılaştırma satır bazlı join değil, **agregat seviyesinde** yapılır: kategori başına toplam = `predictions.fault_type` grubu (`suggestion != IZLE`), kategori başına yanlış = `accuracy_feedback.original_fault_type` grubundaki benzersiz `incident_id` sayısı. Kaynak: `services/ai-service/app/core/accuracy.py`.

**Gerçek test sonucu** (CP6'da doğrulandı): 7 tahminden 1'i düzeltildi → genel doğruluk %85.7; kategori kırılımı ISINMA %75 (4 tahmin, 1 yanlış), BAĞLANTI %100 (3 tahmin, 0 yanlış).

## 7. Eğitim/Few-Shot Verisi

Formel bir ML eğitimi yapılmadığı için "eğitim verisi" kavramı burada **few-shot bağlam + demo/seed verisi** olarak karşılık buluyor: `docs/sample_telemetry.json` içinde 100+ etiketli, gerçekçi Türkçe telemetri örneği (normal + her `fault_type`'tan arızalı senaryolar) bulunur. Bu veri üç amaçla kullanılır:

1. **Seed/demo verisi:** Docker Compose ilk açılışta veya manuel testte gerçekçi telemetri göndermek için.
2. **Prompt few-shot bağlamı:** `SYSTEM_PROMPT` içine gömülü örnekler bu setten temsili şekilde seçildi.
3. **Fallback kural kalibrasyonu:** `rule_fallback.py`'deki eşik sabitlerinin (65°C, %15 paket kaybı vb.) gerçekçi olup olmadığını bu veriyle gözden geçirdik.

## 8. Dürüstçe Belirtilmesi Gereken Sınırlama

Bu ortamda gerçek bir `ANTHROPIC_API_KEY` yapılandırılmadığı için **LLM'in başarılı-çağrı (happy path) davranışı canlı olarak test edilemedi** — her test isteği otomatik olarak `RULE_FALLBACK` yoluna düştü (ki bu da ayrıca doğru davranış: anahtar yokken senkron ve hızlı şekilde fallback'e geçtiği doğrulandı). Prompt/tool şeması Anthropic API dokümantasyonuna göre yazıldı ve kod seviyesinde gözden geçirildi, ama gerçek bir API anahtarıyla uçtan uca doğrulama takım tarafından demo öncesi yapılmalı.

## 9. Kod Referansları

| Bileşen | Dosya |
|---|---|
| LLM istemcisi, prompt, tool şeması, circuit breaker | `services/ai-service/app/core/llm_client.py` |
| Kural tabanlı fallback | `services/ai-service/app/core/rule_fallback.py` |
| Eşik uygulaması (suggestion/priority) | `services/ai-service/app/core/thresholds.py` |
| Tahmin orkestrasyonu (LLM→fallback geçişi) | `services/ai-service/app/core/predictor.py` |
| Atama algoritması (Haversine + skorlama) | `services/ai-service/app/core/assignment.py`, `geo.py` |
| Doğruluk hesaplama | `services/ai-service/app/core/accuracy.py` |
