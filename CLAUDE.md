# NetOpsCell — Proje Talimatları (Claude Code için)

Bu repo Turkcell CodeNight 2026 Final case'i için 3 kişilik bir takım tarafından paralel geliştirilir. Bu dosyayı okuyan her Claude Code oturumu aşağıdaki kurallara uyar.

## Önce oku

1. CodeNight_FINAL_NetOpsCell_Case.pdf — orijinal case (zorunlu/opsiyonel tüm gereksinimler)
2. ARCHITECTURE.md — teknik mimari kararları (stack, DB şemaları, endpoint listesi, event kataloğu, LLM entegrasyonu). Bu kararlar zaten verilmiştir; yeniden tartışmaya açma, sorgulanmadıkça değiştirme.
3. TASK_SPLIT.md — kim hangi klasörden sorumlu, checkpoint takvimi, görev listeleri

## İlk yapman gereken şey

Konuşmanın başında, eğer belirtilmemişse kullanıcıya hangi kişi olduğunu sor (Kişi 1: Identity+Gateway / Kişi 2: Incident+AI+Gamification / Kişi 3: Frontend). Cevaba göre TASK_SPLIT.md'deki ilgili bölümü esas al.

## Klasör sınırları — TAM AYRIK

| Kişi | Sahip olduğu klasör(ler) |
|---|---|
| Kişi 1 | gateway/, services/identity-service/ |
| Kişi 2 | services/incident-service/, services/ai-service/, services/gamification-service/ |
| Kişi 3 | frontend/ |

Kendi klasörünün dışına, özellikle bir başkasının sahip olduğu servis klasörüne dokunma. İstisna: docker-compose.yml, .env.example, EVENTS.md, docs/CONTRACTS.md, kök README.md — bunlar ortak dosyalardır (TASK_SPLIT.md §1.1); değiştirmeden önce kullanıcıya bunun ortak bir dosya olduğunu ve diğer kişilere haber verilmesi gerektiğini hatırlat.

## Checkpoint disiplini (bağlayıcı kural — bkz. TASK_SPLIT.md §9)

- Adım adım ilerlenir; tüm iş bitene kadar entegrasyon sona bırakılmaz. Her checkpoint'te: git pull origin main → smoke test (docker compose up veya ilgili servis) → o checkpoint'in Definition of Done satırını doğrula → bozuksa hemen düzelt → ancak sonra yeni branch aç.
- Kendi görev listeni bitirdiğinde otomatik olarak proje bitti varsayma. Sadece kendi checkpoint'inin DoD'sini karşılayıp karşılamadığını kullanıcıya bildir.
- Bir sonraki checkpoint'in görevlerine geçmeden önce, main'de başkalarının merge ettiği yeni değişiklik olup olmadığını kullanıcıya sor / kontrol etmesini öner (özellikle docs/CONTRACTS.md değiştiyse).
- Branch adı deseni: <isim>/<servis>-<özellik> (örn. ali/identity-jwt-rotation). Bir branch en fazla 1-1.5 saat yaşar; uzun ömürlü kişi-bazlı branch açma.
- Kimse main'e doğrudan push atmaz; küçük PR + hızlı review.

## Ortam / Docker notu

- Native PostgreSQL/Redis kurulumu yok — hepsi docker-compose.yml içinde container. DB driver'lar (asyncpg/psycopg2-binary) sadece pip paketi, native kurulum gerektirmez.
- Servisler arası URL'ler (örn. Incident → AI Service adresi) asla hardcode edilmez; .env'den env-var olarak okunur (native'de localhost:PORT, Docker'da container adı — örn. ai-service:8003). Bu kural baştan uygulanmazsa son entegrasyonda (ve docker compose up diskalifiye kuralında) sorun çıkar.
- Her serviste Dockerfile, iskelet aşamasında (CP1 civarı) yazılıp bir kez build edilir; tamamen sona bırakılmaz.

## Diskalifiye kurallarını asla ihlal etme

- Monolith mimari yasak — her servis bağımsız çalışmalı.
- AI Service asla sabit/hardcoded çıktı döndürmemeli (girdiye göre gerçekten değişmeli) — hem LLM yolu hem fallback yolu için geçerli.
- Servisler ortak/paylaşımlı veritabanı kullanamaz — database-per-service.
- docker compose up ile sistem tek komutla ayağa kalkmalı.

# Behavioral guidelines for this workspace

Behavioral guidelines for this workspace, inspired by Andrej Karpathy's advice on avoiding common LLM coding mistakes.

## 1. Think Before Coding

Do not assume. Surface tradeoffs and ambiguity.

Before implementing:
- State assumptions explicitly.
- If there are multiple interpretations, present them instead of silently choosing one.
- If a simpler approach exists, say so.
- If something is unclear, stop and ask for clarification.

## 2. Simplicity First

Prefer the minimum code that solves the current problem.

- Avoid speculative features.
- Avoid abstractions for one-off code.
- Avoid extra configuration or error handling that was not requested.
- If a 200-line solution could be 50 lines, simplify it.

## 3. Surgical Changes

Touch only what must change.

- Do not refactor unrelated code just because it is nearby.
- Match the existing style.
- Remove only the imports, variables, or functions made unused by your changes.
- Every changed line should trace directly to the request.

## 4. Goal-Driven Execution

Turn tasks into verifiable goals.

Examples:
- Add validation → Write tests for invalid inputs, then make them pass
- Fix the bug → Write a test that reproduces it, then make it pass
- Refactor X → Ensure tests pass before and after

For multi-step work, use a short plan like:
1. Implement the minimal change
2. Verify it with the relevant test or smoke check
3. Stop if the result does not satisfy the goal

## NetOpsCell-specific guidance

- Keep changes scoped to the current module or service.
- Prefer small, reviewable increments over large rewrites.
- Verify with the relevant smoke test or command before claiming completion.
- For this project, favor simple API contracts and clear service boundaries over premature abstraction.
