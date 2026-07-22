# NetOpsCell — Proje Talimatları (Claude Code için)

Bu repo **Turkcell CodeNight 2026 Final** case'i için 3 kişilik bir takım tarafından **paralel** geliştiriliyor. Bu dosyayı okuyan her Claude Code oturumu (hangi bilgisayarda çalışıyor olursa olsun) aşağıdaki kurallara uyar.

## Önce oku

1. `CodeNight_FINAL_NetOpsCell_Case.pdf` — orijinal case (zorunlu/opsiyonel tüm gereksinimler)
2. `ARCHITECTURE.md` — teknik mimari kararları (stack, DB şemaları, endpoint listesi, event kataloğu, LLM entegrasyonu). Bu kararlar **zaten verilmiş**; yeniden tartışmaya açma, sorgulanmadıkça değiştirme.
3. `TASK_SPLIT.md` — kim hangi klasörden sorumlu, checkpoint takvimi, görev listeleri

## İlk yapman gereken şey

Konuşmanın başında, eğer belirtilmemişse kullanıcıya **hangi kişi olduğunu sor** (Kişi 1: Identity+Gateway / Kişi 2: Incident+AI+Gamification / Kişi 3: Frontend). Cevaba göre TASK_SPLIT.md'deki ilgili bölümü (4, 5 veya 6) esas al.

## Klasör sınırları — TAM AYRIK

| Kişi | Sahip olduğu klasör(ler) |
|---|---|
| Kişi 1 | `gateway/`, `services/identity-service/` |
| Kişi 2 | `services/incident-service/`, `services/ai-service/`, `services/gamification-service/` |
| Kişi 3 | `frontend/` |

**Kendi klasörünün dışına, özellikle bir başkasının sahip olduğu servis klasörüne dokunma.** İstisna: `docker-compose.yml`, `.env.example`, `EVENTS.md`, `docs/CONTRACTS.md`, kök `README.md` — bunlar ortak dosyalardır (TASK_SPLIT.md §1.1), değiştirmeden önce kullanıcıya bunun ortak bir dosya olduğunu ve diğer kişilere haber verilmesi gerektiğini hatırlat.

## Checkpoint disiplini (bağlayıcı kural — bkz. TASK_SPLIT.md §9)

- **Adım adım ilerlenir, tüm iş bitene kadar entegrasyon sona bırakılmaz.** Her checkpoint'te: `git pull origin main` → smoke test (`docker compose up` veya ilgili servis) → o checkpoint'in "Definition of Done" satırını doğrula → bozuksa hemen düzelt → ancak sonra yeni branch aç.
- Kendi görev listeni bitirdiğinde **otomatik olarak "proje bitti" varsayma.** Sadece kendi checkpoint'inin DoD'sini karşılayıp karşılamadığını kullanıcıya bildir.
- Bir sonraki checkpoint'in görevlerine geçmeden önce, `main`'de başkalarının merge ettiği yeni değişiklik olup olmadığını kullanıcıya sor / kontrol etmesini öner (özellikle `docs/CONTRACTS.md` değiştiyse).
- Branch adı deseni: `<isim>/<servis>-<özellik>` (örn. `ali/identity-jwt-rotation`). Bir branch en fazla 1-1.5 saat yaşar; uzun ömürlü kişi-bazlı branch açma.
- Kimse `main`'e doğrudan push atmaz; küçük PR + hızlı review.

## Ortam / Docker notu

- Native PostgreSQL/Redis kurulumu **yok** — hepsi `docker-compose.yml` içinde container. DB driver'lar (`asyncpg`/`psycopg2-binary`) sadece pip paketi, native kurulum gerektirmez.
- Servisler arası URL'ler (örn. Incident → AI Service adresi) **asla hardcode edilmez**, `.env`'den env-var olarak okunur (native'de `localhost:PORT`, Docker'da container adı — örn. `ai-service:8003`). Bu kural baştan uygulanmazsa son entegrasyonda (ve `docker compose up` diskalifiye kuralında) sorun çıkar.
- Her serviste Dockerfile, iskelet aşamasında (CP1 civarı) yazılıp bir kez build edilir; tamamen sona bırakılmaz.

## Diskalifiye kurallarını asla ihlal etme

- Monolith mimari yasak — her servis bağımsız çalışmalı.
- AI Service **asla** sabit/hardcoded çıktı döndürmemeli (girdiye göre gerçekten değişmeli) — hem LLM yolu hem fallback yolu için geçerli.
- Servisler ortak/paylaşımlı veritabanı kullanamaz — database-per-service.
- `docker compose up` ile sistem tek komutla ayağa kalkmalı.
