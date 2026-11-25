# NEXUS MVP — Görevler

Durum: [x] uygulandı · [ ] açık · Şeritler (SCOPE §6.2) başlıklarda.

## F0 · Ortam ve yürüyen iskelet — oku: kural md'leri, SCOPE §4
- [x] Repo yapısı (§3.2), `requirements.txt` sabit sürümler, `config/.env.example` — bitti: dosyalar mevcut
- [x] `scripts/list_models.sh` — bitti: modeller ve inference profile'lar listelenir
- [ ] Kiro: `scripts/list_models.sh` çalıştır, `BEDROCK_MODEL_ID` seç — bitti: README'de model yazılı
- [x] `scripts/deploy_all.sh` (kova, input yükleme, AgentCore, Lambda'lar, UI) — bitti: betik idempotent
- [ ] Kiro: SES alan adı/MX kontrolü — bitti: durum raporlanır (yoksa yedek tetik)

## F1 · Sözleşmeler + veri katmanı — oku: 00_ortak_veri_semalari.md, nexus-data.md
- [x] `src/contracts/schemas.py` v1.1 — bitti: `pytest tests/contracts -q`
- [x] `src/data_access/loader.py` — bitti: 15 sayfa yüklenir
- [ ] Koruma testi (§7.1) — bitti: `pytest tests/contracts -q` geçer

## F2 · [Şerit A] Impact + Risk tool'ları — oku: 03_*, 02_*
- [ ] Impact I1–I13 + Strands sarmalayıcı — bitti: `pytest tests/unit/impact -m "not llm"`
- [ ] Risk deterministik tool'ları — bitti: `pytest tests/unit/risk -m "not llm"`

## F3 · [Şerit B] Signal + [A] Risk LLM — oku: 01_*, 02_*
- [ ] Signal çıkarım/eşleştirme/gürültü — bitti: S1 alanları (§7.2), `-m llm`
- [ ] Risk `DisKosulBileseni` — bitti: 4,4 × 5 = 22 Yüksek

## F4 · [Şerit C] Options + Decision — oku: 04_*, 05_*
- [ ] 6 strateji, C1–C6 — bitti: `pytest tests/unit/options`
- [ ] Simülasyon, ÇKKV, MILP (D15), gerekçe rakam testi — bitti: `pytest tests/unit/decision`

## F5 · Orkestratör + AgentCore — oku: 00_orkestrator_*
- [ ] `src/orchestrator/orchestrator.py` (`sinyal_isle`, `toplu_tarama`, `insan_karari`) — bitti: yerel e2e
- [x] `src/app.py` eylem yönlendirme — bitti: `python -c "import src.app"`
- [ ] Deploy (`scripts/deploy_all.sh`) + Observability — bitti: `agentcore invoke '{"eylem":"SINYAL_ISLE","sinyal_no":"SG-2611-001"}'` → S3'te 5 çıktı + `Onay Bekliyor`

## F6 · [Şerit D] Otonom tetik + API + UI — oku: SCOPE §4.4–4.8
- [x] `src/triggers/email_trigger/handler.py` (MIME, PII, eşleşme/yeni sinyal, idempotency) — bitti: `scripts/send_test_email.sh` → yeni run
- [x] `src/api/handler.py` (runs, decisions, decision, email; CORS, anahtar) — bitti: `curl -H x-api-key ... /runs`
- [x] `ui/` 4 ekran + DEMO modu — bitti: `ui/index.html` backend'siz açılır
- [ ] SES alma kuralı (opsiyonel, §6.3 kesme sırası 4)
- [ ] Bulutta: Onayla → `decisions/<olay>.json` `Onaylandı`

## F7 · Demo ve teslim — oku: hackathon_kural_seti.md §7
- [x] `scripts/demo_reset.py` (D17) — bitti: S3 durum önekleri temizlenir, toplu tarama tetiklenir
- [x] Kök README (kurulum, deploy, hesap ID, bölge)
- [ ] `docs/mimari/` çizim, ekran görüntüleri, 1 dk video, prova ≤ 5 dk
- [ ] Kontrol listesi (hackathon_kural_seti.md §7)

## F8 · Opsiyonel
- [ ] (opsiyonel) S2/S3 kabul testleri
- [ ] (opsiyonel) İkinci sinyalde yeniden hesaplama
- [ ] (opsiyonel) what-if
