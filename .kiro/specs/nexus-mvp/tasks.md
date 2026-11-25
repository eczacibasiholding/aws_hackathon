# Implementation Plan: NEXUS MVP

## Overview

Bu plan, NEXUS MVP'nin AWS üzerinde çalışan çok ajanlı sürümünü belgeler: sözleşmeler → veri erişimi → LLM katmanı → beş ajan → orkestratör → AgentCore Runtime → e-posta tetikleyici → API → UI/harita → dağıtım. Her ajan görevi S1 referans senaryosu (SG-2611-001 / SV-26-1184 / MT100054) ile doğrulanır (SCOPE §7.2). Testler `NEXUS_LLM=off` ile deterministik çalışır; mevcut durum 43 passed, 1 skipped.

## Tasks

- [x] 1. Sözleşmeler ve proje yapısı
  - [x] 1.1 `src/contracts/schemas.py` içinde v1.1 Pydantic modellerini tanımla
    - `Sozlesme` tabanı (tanımsız alan reddi), `Zarf`, `Uyari`, `KaynakRef`
    - SignalOutput, RiskOutput, ImpactOutput, OptionsOutput, DecisionOutput, KararKaydi ve alt modeller
    - LLM sınır modelleri: `SignalLLMCikarimi`, `DisKosulBileseni`, `DecisionMetinLLM`
    - _Requirements: 1.1, 1.2, 1.4_
  - [x] 1.2 Sözleşme koruma testlerini yaz (`tests/contracts/test_koruma.py`)
    - _Requirements: 1.3_
  - [x] 1.3 Sabit sürümlü `requirements.txt` oluştur (strands-agents, bedrock-agentcore, pandas, pydantic, pulp, scipy, boto3, aws-opentelemetry-distro)
    - _Requirements: 14.4_

- [x] 2. Veri erişimi ve LLM katmanı
  - [x] 2.1 `src/data_access/loader.py`: `NexusData`, `load_data`, `load_cached` (yerel + `s3://`)
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 2.2 `src/common/llm.py`: `llm_acik`, `structured`, `text` (Strands + Bedrock, `NEXUS_LLM=off` yedeği)
    - _Requirements: 13.1, 13.2, 13.3_

- [x] 3. Signal Agent
  - [x] 3.1 `tools/extraction.py` ve `tools/matching.py`: LLM çıkarımı, kural yedeği, sevkiyat/malzeme eşleme
    - _Requirements: 4.1, 4.3_
  - [x] 3.2 `agent.py run()`: ayıklama (`AYIKLA`) ve SignalOutput üretimi
    - _Requirements: 4.1, 4.2_
  - [x] 3.3 S1 birim testleri (`tests/unit/signal/test_signal_agent.py`)
    - _Requirements: 4.4_

- [x] 4. Impact Agent
  - [x] 4.1 `tools/calc.py`: zincir çözümleme, tüketim, kapsama, tükenme, kullanılabilir tarih, açık gün, duruş maliyeti, ceza, etki puanı
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [x] 4.2 `agent.py run()`: malzeme başına ImpactOutput
    - _Requirements: 5.5_
  - [x] 4.3 S1 birim testleri (`tests/unit/impact/test_impact_agent.py`)
    - _Requirements: 5.6_

- [x] 5. Risk Agent
  - [x] 5.1 `tools/scoring.py`: taraf seçimi, performans ve finansal puan
    - _Requirements: 6.1_
  - [x] 5.2 Dış koşul bileşeni (LLM sınır modeli + kural yedeği), Olasılık × Etki ve kademe
    - _Requirements: 6.2, 6.3_
  - [x] 5.3 Birim testleri (`tests/unit/risk/test_risk_agent.py`)
    - _Requirements: 6.5_

- [x] 6. Options Agent
  - [x] 6.1 `sourcing/tools.py` ve `logistics/tools.py`: kaynak, rota, süre, maliyet, CO2
    - _Requirements: 7.1_
  - [x] 6.2 `agent.py run()`: strateji bileşenleri, `KisitKontrolu`, `ElenenKaynak`
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 6.3 S1 testi: 6 strateji (`tests/unit/options/test_options_s1.py`)
    - _Requirements: 7.4_

- [x] 7. Decision Agent
  - [x] 7.1 `tools/simulation.py`: `inflows`, `simulate_inventory`
    - _Requirements: 8.1_
  - [x] 7.2 `tools/scoring.py`: maliyet kalemleri, stok taşıma, MCDA, sıralama
    - _Requirements: 8.2_
  - [x] 7.3 `tools/milp.py`: `solve_milp` (PuLP → SciPy → sayım yedeği)
    - _Requirements: 8.3_
  - [x] 7.4 `tools/rationale.py` + `prompts/gerekce.py`: izinli sayılar, sayı testi, şablon gerekçe
    - _Requirements: 8.4, 8.5_
  - [x] 7.5 S1 testi: S1-HIB önerisi (`tests/unit/decision/test_decision_s1.py`)
    - _Requirements: 8.6_
  - [ ]* 7.6 PuLP için gerçek CBC çözücü arka ucunu Runtime paketine ekle (şu an SciPy/sayım yedeği devrede)
    - _Requirements: 8.3_

- [x] 8. Orkestratör
  - [x] 8.1 `store.py`: S3/yerel JSON `Store.put / get / list`
    - _Requirements: 9.3_
  - [x] 8.2 `orchestrator.py sinyal_isle`: ajan sırası, durum makinesi (KAPAT/IZLEME/UYARI/ONAY_BEKLIYOR/HATA), OTel span'leri
    - _Requirements: 9.1, 9.2, 9.5, 9.6_
  - [x] 8.3 Karar Kaydı üretimi (`decisions/`) ve SES onay bildirimi (`_bildir`)
    - _Requirements: 9.4_
  - [x] 8.4 `insan_karari` ve `toplu_tarama`
    - _Requirements: 9.7, 10.1, 10.2_
  - [x] 8.5 Uçtan uca S1 testi (`tests/e2e/test_s1_akis.py`)
    - _Requirements: 9.1, 9.4_
  - [ ] 8.6 Aynı riske ait ikinci sinyali (SG-2611-002) mevcut Karar Kaydı'na bağla
    - Şu an ayrı bir karar kaydı oluşturuluyor (D7)
    - _Requirements: 4.1, 9.4_

- [x] 9. AgentCore Runtime
  - [x] 9.1 `src/app.py`: `BedrockAgentCoreApp`, `EYLEMLER` (SINYAL_ISLE, TOPLU_TARAMA, INSAN_KARARI)
    - _Requirements: 9.1, 10.1_
  - [x] 9.2 `nexus_runtime` dağıtımı (direct_code_deploy, PYTHON_3_13, observability)
    - _Requirements: 14.1_

- [x] 10. E-posta tetikleyici
  - [x] 10.1 `handler.py`: MIME ayrıştırma, PII temizliği, normalizasyon
    - _Requirements: 3.1, 3.2_
  - [x] 10.2 Sinyal eşleme / yeni sinyal kaydı (`signals/`) ve AgentCore çağrısı
    - _Requirements: 3.3, 3.4, 3.5_
  - [x] 10.3 S3 ObjectCreated bildirimi ve `inbound-email/` 1 günlük yaşam döngüsü
    - _Requirements: 3.1, 3.6_
  - [ ] 10.4 SES gelen e-posta alım kuralını (receipt rule) yapılandır
    - Doğrulanmış alan adı gerektirir; şimdilik giriş `POST /email` ve `send_test_email.sh` ile
    - _Requirements: 3.1_
  - [ ] 10.5 SES bildirim gönderici kimliğinin doğrulanmasını tamamla
    - _Requirements: 9.4_

- [x] 11. API
  - [x] 11.1 `src/api/handler.py`: `/runs`, `/runs/{id}`, `/decisions`, `/decision`, `/email`, `/health`, CORS
    - _Requirements: 11.1, 11.4, 11.5_
  - [x] 11.2 `x-api-key` doğrulaması; `GET /map` herkese açık
    - _Requirements: 11.2, 11.3_

- [x] 12. UI ve harita
  - [x] 12.1 `ui/index.html` S3 statik web sitesi
    - _Requirements: 12.1_
  - [x] 12.2 `scripts/build_map_data.py` → `map/`; `frontend/tedarik-zinciri.html` `AJANLAR` → `GET /map`; CloudFront yayını
    - _Requirements: 12.2, 12.3_

- [x] 13. Dağıtım ve demo betikleri
  - [x] 13.1 `scripts/deploy_all.sh`, `deploy_frontend.sh`, `setup_frontend_infra.sh`
    - _Requirements: 14.1_
  - [x] 13.2 `scripts/demo_reset.py`, `scripts/send_test_email.sh`
    - _Requirements: 14.2, 14.3_
  - [x] 13.3 Bulut S1 doğrulaması: ANALIZ → Yüksek → S1-HIB → ONAY_BEKLIYOR
    - Bilinen sapma: olasılık 4,2 (LLM dış koşul puanı), beklenen 4,4; kademe Yüksek
    - _Requirements: 6.5, 8.6, 9.4_

- [ ] 14. Kabul testlerinin genişletilmesi
  - [ ] 14.1 S2 senaryosu tam kabul testi
    - _Requirements: 9.1, 9.2_
  - [ ] 14.2 S3 senaryosu tam kabul testi
    - _Requirements: 9.1, 9.2_
  - [x] 14.3 Gürültü sinyalleri için orkestratör akış testi (tests/e2e/test_s1_akis.py::test_gurultu_kapat) (SG-2611-013…017, SG-2610-*)
    - _Requirements: 4.2, 6.4_

- [ ]* 15. What-if analizi (F8)
  - MVP kapsamı dışında (D7); şema modelleri (`WhatIfIstegi`, `WhatIfKarsilastirma`) ve `what_if_gun` parametresi mevcut, UI/API akışı yok
  - _Requirements: 5.1_

## Notes

- `*` ile işaretli görevler isteğe bağlıdır.
- Sayısal beklentiler yalnızca testlerde kullanılır; `src/` koduna veya istemlere kopyalanmaz (KÇ6).
