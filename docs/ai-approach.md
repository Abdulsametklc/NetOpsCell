# NetOpsCell — AI Yaklaşım Dokümanı

Case Bölüm 5, üç yaklaşımdan birini serbest bırakıyor: (a) klasik ML, (b) kural+ML hibrit, (c) LLM API entegrasyonu. Bu projede **(c) LLM API entegrasyonu, birincil fallback olarak kendi eğittiğimiz ML modeli** seçildi. Bu doküman neyi, neden, nasıl yaptığımızı ve gerçekte test edip edemediğimizi anlatır.

## 1. Neden LLM + Eğitilmiş Model, Bilinçli Trade-off

LLM'i birincil tahmin motoru olarak kullanmanın gerekçesi değişmedi:

- **Hız:** Etiketli veri toplama + model eğitimi + değerlendirme döngüsü olmadan, prompt mühendisliğiyle makul kalitede bir sınıflandırıcı hızlıca elde edilir — hackathon zaman kısıtında değerli.
- **Esneklik:** Telemetri paternleri genişletildiğinde (yeni arıza türü, yeni sinyal kombinasyonu) yeniden eğitim gerekmeden prompt/few-shot örnekleri güncellenir.
- **Açıklanabilirlik:** LLM her tahminle birlikte kısa bir gerekçe (`confidence_explanation`) üretir — jüri demo'sunda "neden bu tahmin?" sorusuna doğrudan cevap.

Ancak başlangıçta LLM'e ulaşılamadığı durumlar için yazılan deterministik if/else kural motoru (`rule_fallback.py`), kendi eğittiğimiz ML modeli bonusunu (+8, case §12.1) hedeflemiyordu — sonradan bu karar gözden geçirildi: LLM'e ulaşılamadığında devreye giren fallback artık **gerçek, eğitilmiş bir sınıflandırıcı** (bkz. §7.1). Bu, LLM birincil yolunu, mesaj kuyruğu (+5), kategori bazlı doğruluk kırılımı (+3) ve gerçek zamanlı bildirim (+2) bonuslarını bozmadan ek bir bonusu (+8) karşılamanın en düşük riskli yolu oldu.

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

AI Service'in kendisi ayaktayken bile dış LLM API'si (ağ sorunu, rate limit, geçici kesinti) yanıt vermeyebilir. Bu durumda **asla sabit/mock bir çıktı dönülmez** — case'in diskalifiye kuralı ("AI servisi mock/hardcoded ise değerlendirme dışı") burada özellikle önemli, çünkü fallback yolu da gerçek bir algoritma: eğitilmiş ML modeli (bkz. §7.1), o da yoksa deterministik if/else kural motoru:

```python
# rule_fallback.py — son care savunma katmani, model.joblib bir sekilde
# yuklenemediginde devreye girer; girdiye gore GERCEKTEN degisir
if temperature > 65:        contributions[ISINMA] += 0.35
if packet_loss > 15:        contributions[BAGLANTI] += 0.30
if signal_strength < -100:  contributions[BAGLANTI] += 0.20
if power_status == KESINTIDE: contributions[GUC_KESINTISI] += 0.35
if recent_fault_count >= 2: contributions[DONANIM] += 0.15
```

**Devreye girme sırası:**
1. `ANTHROPIC_API_KEY` tanımlı değilse → doğrudan ML modeli fallback (senkron, network çağrısı bile yapılmaz)
2. LLM çağrısı 4sn'de yanıt vermezse veya hata verirse → 1 retry
3. Retry de başarısız olursa → ML modeli fallback + **circuit breaker**: art arda 3 başarısızlık sonrası 30sn'lik sogutma penceresinde LLM hiç denenmez, doğrudan fallback kullanılır (dış API'yi gereksiz yormamak için)
4. ML modeli dosyası (`model.joblib`) bir şekilde yüklenemezse → kural tabanlı if/else motoru (en son çare)

Her `predictions` kaydında `method` alanı (`LLM` / `ML_MODEL` / `RULE_FALLBACK`) saklanır — hangi yolun devrede olduğu her zaman şeffaf.

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
4. **ML modeli eğitim verisi:** Aynı 122 örnek, aşağıdaki §7.1'de anlatıldığı gibi doğrudan bir sınıflandırıcı eğitmek için de kullanıldı.

### 7.1. Kendi Eğittiğimiz ML Modeli (bonus +8)

LLM'e ulaşılamadığında devreye giren fallback, artık deterministik if/else değil, **gerçekten eğitilmiş bir sınıflandırıcı**. Aşağıda özet var; **tam detaylı süreç, tüm ara sonuçlar ve metodoloji için bkz. `docs/ml-model.md`.**

**Veri:** `services/ai-service/app/ml/training_data.json` (`docs/sample_telemetry.json`'un servis içine kopyası — her servis kendi build context'i içinde bağımsız olmalı, kök `docs/` klasörüne Docker build sırasında erişilemiyor). 122 örnek, her biri `fault_type` (6 kategori: DONANIM, GUC_KESINTISI, BAGLANTI, YAZILIM, ISINMA, BELIRSIZ) ve `severity` ile etiketli.

**Süreç:** `services/ai-service/app/ml/train_model.py` — `python -m app.ml.train_model` ile çalıştırılır:

1. `signal_strength`, `packet_loss`, `temperature`, `recent_fault_count`, `power_status` (KESINTIDE → 1/0) feature'ları çıkarılır.
2. **4 farklı algoritma** aday olarak tanımlanır (hepsi `StandardScaler` + sınıflandırıcı pipeline'ı): `LogisticRegression`, `SVC` (RBF kernel, `probability=True`), `RandomForestClassifier`, `GradientBoostingClassifier`.
3. Her aday için **`GridSearchCV` ile hiperparametre araması** yapılır (`clf__C`, `clf__gamma`, `clf__max_depth`, `clf__n_estimators` vb. — tam gridler `train_model.py`'de), her kombinasyon **5-fold stratified cross-validation** ile 4 metrik üzerinden değerlendirilir: accuracy, precision (macro), recall (macro), f1 (macro). Sadece varsayılan hiperparametrelerle tek bir train/test ayrımına güvenmek yerine hem arama hem CV kullanılması, 122 örnek gibi küçük bir veri setinde tesadüfi bir "iyi" split'in yanıltıcı sonuç vermesini engeller.
4. Her algoritmanın **en iyi (tuned) CV f1 (macro) skoru** karşılaştırılır, en yükseği **seçilir**, hiç görmediği bir holdout üzerinde bir kez değerlendirilir (sızıntı önleme detayı aşağıda), sonra aynı hiperparametrelerle **tüm veriyle** (122 örneğin tamamı) yeniden eğitilip production modeli olarak kaydedilir.
5. Karşılaştırma tablosu + seçilen modelin holdout raporu + seçilen hiperparametreler `app/ml/model_comparison.md`'ye yazılır; nihai pipeline `app/ml/model.joblib` olarak `joblib.dump()` ile kaydedilip repoya commit edilir (imaj build edilirken `COPY . .` ile servise dahil olur, yeniden eğitim gerekmez).

**Sızıntı kontrolü (önemli metodolojik düzeltme):** İlk versiyonda holdout seti, algoritma seçimi (CV) tüm 122 örnek üzerinde yapıldıktan SONRA aynı veriden ayrılıyordu — yani hangi algoritmanın kazandığı kararı, holdout'taki satırları da dolaylı olarak "görerek" veriliyordu. Bu, raporlanan holdout doğruluğunu iyimser gösteren bir sızıntıydı (ilk ölçüm: SVM, %92 holdout doğruluğu). Düzeltildi: artık **holdout seti (%20, 25 örnek) model seçimi/arama başlamadan önce ayrılıyor ve GridSearchCV'nin 5-fold CV'sine hiç dahil edilmiyor**; algoritma+hiperparametre seçimi sadece kalan pool (97 örnek) üzerinde yapılıyor, holdout değerlendirmesi seçim bittikten sonra bir kez, hiç görülmemiş veriyle yapılıyor. Veri setinde ayrıca tam duplike satır veya tekrarlanan istasyon kaydı olup olmadığı da kontrol edildi — **0 duplike** bulundu, satır bazlı bir sızıntı yok.

**Gerçek (sızıntısız, hiperparametre-optimize edilmiş) karşılaştırma sonucu** (GridSearchCV + 5-fold CV, sadece pool üzerinde — `app/ml/model_comparison.md`):

| Algoritma | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | En iyi parametreler |
|---|---|---|---|---|---|
| **SVM (seçildi)** | 0.906 | 0.881 | 0.861 | 0.856 | `C=1.0, gamma=1.0` |
| LogisticRegression | 0.895 | 0.873 | 0.850 | 0.845 | `C=0.1` |
| RandomForest | 0.886 | 0.838 | 0.828 | 0.817 | `max_depth=4, min_samples_leaf=1, n_estimators=200` |
| GradientBoosting | 0.865 | 0.815 | 0.806 | 0.796 | `learning_rate=0.1, max_depth=3, n_estimators=150` |

Hiperparametre araması yapılmadan önce (varsayılan ayarlarla) LogisticRegression öndeydi (f1=0.834); arama sonrası SVM açık ara öne geçti (f1=0.856) — yani "en iyi algoritma" sorusu hiperparametrelere duyarlı, bu yüzden arama adımı atlanmamalı. Hiç görülmemiş holdout setinde (25 örnek) **%88 doğruluk** (varsayılan-ayarlı ölçüm: %80; ilk sızıntılı ölçüm: %92 — üçü de farklı şeyler ölçüyor, karıştırılmamalı). Kategori bazlı: DONANIM %100 f1, BELİRSİZ %92 f1, **GUC_KESINTISI %89 f1** (varsayılan ayarlarda %60'tı — hiperparametre aramasının en büyük kazancı), BAGLANTI %89 f1, ISINMA %80 f1, YAZILIM %67 f1 (sadece 2 test örneği — küçük veri setinin aşamayacağımız tek sınırlaması, bkz. §8).

**Çıkarım mantığı** (`app/core/ml_fallback.py`): Model her sınıf için bir olasılık üretir (`predict_proba`). `probability = 1 - P(BELİRSİZ)` — yani "bu telemetri gerçek bir arızanın işareti mi" olasılığı; `fault_type` ise BELİRSİZ dışındaki en olası kategori. Örnek doğrulama (rastgele girdilerle, gerçekten değişiyor mu diye manuel test edildi):

| Girdi | probability | fault_type |
|---|---|---|
| Normal (sinyal -70dBm, sıcaklık 25°C) | 0.114 | YAZILIM (düşük olasılık, IZLE eşiğinin altında) |
| Güç kesintisi + yüksek sıcaklık + paket kaybı | 0.976 | BAGLANTI |
| Çok zayıf sinyal (-118dBm) + yüksek paket kaybı | 0.985 | BAGLANTI |
| Yüksek sıcaklık (85°C) tek başına | 0.987 | ISINMA |

**Sentetik (eğitim verisinde hiç geçmeyen) veriyle ek doğrulama** (`tests/test_ml_fallback_synthetic.py`, bkz. §9): hiperparametre aramasından önce %75 (9/12), sonra **%83.3 (10/12)** — model gerçekten iyileşti, sadece raporlanan sayı değişmedi. Kalan 2 zayıflık (BELİRSİZ↔YAZILIM karışıklığı) hâlâ duruyor ve testte `xfail` ile açıkça işaretli (bkz. §8).

Model dosyası (`model.joblib`) bir şekilde eksik/bozuksa `ml_fallback.py`, eski `rule_based_predict`'e düşer — üçüncü ve en son savunma katmanı (bkz. §5).

## 8. Dürüstçe Belirtilmesi Gereken Sınırlamalar

- Bu ortamda gerçek bir `ANTHROPIC_API_KEY` yapılandırılmadığı için **LLM'in başarılı-çağrı (happy path) davranışı canlı olarak test edilemedi** — her test isteği otomatik olarak ML modeli fallback yoluna düştü (ki bu da ayrıca doğru davranış: anahtar yokken senkron ve hızlı şekilde fallback'e geçtiği doğrulandı). Prompt/tool şeması Anthropic API dokümantasyonuna göre yazıldı ve kod seviyesinde gözden geçirildi, ama gerçek bir API anahtarıyla uçtan uca doğrulama takım tarafından demo öncesi yapılmalı.
- ML modeli 122 örnekle eğitildi — bu, üretim standardında büyük bir veri seti değil (özellikle YAZILIM sınıfında holdout performansı belirgin şekilde daha zayıf kalıyor — f1 %67, sadece 2 test örneği). Jüriye karşı dürüstçe: bu bonus maddesinin "gerçekten eğitilmiş, train/test ayrımı yapılmış, doğruluğu ölçülmüş bir model" kriterini karşıladığı, ama üretim kalitesinde bir ML sistemi olmadığı açıkça belirtilmeli.
- Algoritma seçimi (hiperparametre araması dahil) CV ortalamasına dayanıyor; veri seti küçük olduğu için CV skorları arasındaki fark (SVM 0.856 vs LogisticRegression 0.845 f1-macro, tuned) istatistiksel olarak büyük bir marj değil. Daha fazla etiketli veri toplansa sıralama değişebilir — bu, mevcut kararın "kesin" değil "bu veriyle en iyisi" olduğu anlamına gelir; dokümantasyonda böyle sunulmalı.
- **Sızıntı geçmişi (şeffaflık için bilerek bırakıldı):** İlk yazılan karşılaştırma scripti, holdout'u model seçiminden sonra aynı havuzdan ayırıyordu; bu, holdout doğruluğunu %92'ye şişiren bir sızıntıydı. Sonradan fark edilip düzeltildi (bkz. §7.1) — düzeltilmiş, sızıntısız, varsayılan hiperparametrelerle gerçek sayı %80; hiperparametre araması eklendikten sonra (gerçek bir iyileşme, sızıntı değil) %88'e çıktı. Bu, "veri sızıntısı" kavramının nasıl fark edilip düzeltildiğinin somut bir örneği olarak bilerek dokümante edildi.
- **Sentetik (eğitim verisinde hiç geçmeyen, elle yazılmış) verilerle ek doğrulama** yapıldı (`tests/test_ml_fallback_synthetic.py`, 12 net + 2 belirsiz senaryo): hiperparametre aramasından önce doğruluk %75 (9/12), sonra **%83.3 (10/12)** — model gerçekten iyileşti (bir senaryo, yüksek paket kaybının artık doğru BAGLANTI olarak tahmin edilmesi, testte `xfail(strict=True)` ile "beklenmedik geçiş" olarak otomatik yakalandı ve güncellendi). Kalan tek bilinen zayıflık: **model BELİRSİZ'i bazen YAZILIM ile karıştırıyor** (örn. tertemiz bir telemetri YAZILIM'a kayabiliyor). Sebebi: eğitim verisindeki YAZILIM örnekleri (10 tane) "hiçbir eşiği net aşmayan ama her şey hafif yüksek" gibi bulanık bir bölgeyi kaplıyor, bu da tertemiz BELİRSİZ bölgesiyle örtüşüyor. Bu senaryolarda `probability` yine de 0.40 IZLE eşiğinin altında kaldığı için iş kuralı (izleme/vaka açma kararı) yanlış etkilenmiyor — ama `fault_type` etiketi yanlış çıkabiliyor. Bilinçli olarak testte `xfail` ile işaretlendi, gizlenmedi.

## 9. Kod Referansları

| Bileşen | Dosya |
|---|---|
| LLM istemcisi, prompt, tool şeması, circuit breaker | `services/ai-service/app/core/llm_client.py` |
| ML modeli eğitim + çoklu-algoritma karşılaştırma scripti | `services/ai-service/app/ml/train_model.py` |
| Model karşılaştırma raporu (4 algoritma, 4 metrik) | `services/ai-service/app/ml/model_comparison.md` |
| Sentetik veriyle ek genelleme testi | `services/ai-service/tests/test_ml_fallback_synthetic.py` |
| ML modeli çıkarım (fallback) | `services/ai-service/app/core/ml_fallback.py` |
| Kural tabanlı fallback (en son çare) | `services/ai-service/app/core/rule_fallback.py` |
| Eşik uygulaması (suggestion/priority) | `services/ai-service/app/core/thresholds.py` |
| Tahmin orkestrasyonu (LLM→fallback geçişi) | `services/ai-service/app/core/predictor.py` |
| Atama algoritması (Haversine + skorlama) | `services/ai-service/app/core/assignment.py`, `geo.py` |
| Doğruluk hesaplama | `services/ai-service/app/core/accuracy.py` |
