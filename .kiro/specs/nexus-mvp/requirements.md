# NEXUS MVP — Gereksinimler (EARS)

> Kaynak: SCOPE §6.1 "bitti" kriterleri + §7.2 S1 kabul tablosu. What-if gereksinimi yazılmaz (D7).
> Beklenen değerler yalnızca testlerde, cevap anahtarından okunur (KÇ6).

## R0 · Ortam (F0) — SCOPE §4.3, §9; hackathon-rules.md
- R0.1 Sistem, model kimliğini YALNIZCA `BEDROCK_MODEL_ID` ortam değişkeninden OKUYACAKTIR. (SCOPE §4.3, D5)
- R0.2 Runtime buluttan çağrıldığında, sistem Bedrock'tan cevap DÖNDÜRECEKTİR. (SCOPE §6.1 F0)
- R0.3 Kök README hesap ID'sini, bölgeyi ve modeli İÇERECEKTİR. (SCOPE §6.1 F0, §6.3)
- R0.4 Bağımlılık sürümleri sabitlenmiş OLACAKTIR. (KÇ11)

## R1 · Sözleşmeler ve veri katmanı (F1) — 00_ortak_veri_semalari.md, nexus-data.md, 00_orkestrator_veri_kurallari.md
- R1.1 Sistem, girdi dosyasını akış başına BİR KEZ yükleyecek; `PO No` string, `"-"` → `None`, `00_Rehber` atılacaktır.
- R1.2 `NEXUS_INPUT_URI` `s3://` ile başlarsa, veri katmanı S3'ten OKUYACAKTIR. (SCOPE §4.6)
- R1.3 `KararKaydi` v1.1 alanlarını içerecektir. (SCOPE D10, §5.1)
- R1.4 `src/` altında `nexus_answer_key` referansı, S1 cevap sabitleri ve Bedrock dışı LLM SDK import'u BULUNMAYACAKTIR. (SCOPE §7.1 koruma testi)

## R2 · Impact + Risk tool'ları (F2) — 03_impact_agent_kapsam_gorev.md, 02_risk_agent_kapsam_gorev.md
- R2.1 SG-2611-001 analiz edildiğinde, Impact kullanılabilir tarihi 10.12 (15. gün), kapsama 9,89 gün, tükenme 04.12 21:16 ÜRETECEKTİR. (§7.2)
- R2.2 Impact duruş 5,11 gün, duruş maliyeti, ceza (4 sipariş) ve aksiyonsuz maliyeti tolerans içinde (TRY ±1, gün ±0,01) ÜRETECEKTİR; etki puanı 5. (§7.2)
- R2.3 Etki veya olasılık yoksa, Risk puan ve kademe ÜRETMEYECEKTİR. (R-K4)

## R3 · Signal + Risk LLM (F3) — 01_signal_agent_veri_kurallari.md, 02_*
- R3.1 SG-2611-001 işlendiğinde, Signal `SV-26-1184`, `MT100054`, 8 gün gecikme ve Mersin ipucunu ÇIKARACAKTIR. (§7.2)
- R3.2 Gürültü sinyali geldiğinde, Signal `AYIKLA` kararı ve gerekçe VERECEKTİR.
- R3.3 S1 için Risk Olasılık 4,4 × Etki 5 = 22 → Yüksek ÜRETECEKTİR. (§7.2)

## R4 · Options + Decision (F4) — 04_options_agent_kapsam_gorev.md, 05_decision_agent_kapsam_gorev.md
- R4.1 S1 için Options 6 strateji ÜRETECEKTİR (C1–C6 kısıtları uygulanmış). (§7.2)
- R4.2 Decision S1-HIB'i ÖNERİLEN olarak, duruş 0 ve toplam maliyet tolerans içinde SEÇECEKTİR; MILP amacı raporlanacaktır. (§7.2, D15)
- R4.3 Gerekçe metnindeki her rakam `OneriRakamlari`'ndan gelecektir (gerekçe rakam testi). (05_* , K6)
- R4.4 MILP çözülemezse, sistem `MILP_YAPILAMADI` uyarısıyla ÇKKV sonucunu SUNACAKTIR. (D15)

## R5 · Orkestratör + AgentCore (F5) — 00_orkestrator_kapsam_gorev.md, SCOPE §4.1, §4.7
- R5.1 `SINYAL_ISLE` SG-2611-001 buluttan çağrıldığında, sistem S3 `runs/<run_id>/` altına 5 agent çıktısı ve `decisions/` altına `Onay Bekliyor` kaydı YAZACAKTIR.
- R5.2 Herhangi bir adımda sözleşme/Bedrock hatası olursa, sistem `HATA` durumuna geçip kısmi sonucu "tamamlanamadı" olarak YAZACAKTIR.
- R5.3 Orkestratör LLM ÇAĞIRMAYACAKTIR. (K5)
- R5.4 Her orkestratör adımı Observability'de ayrı span olarak GÖRÜNECEKTİR; kişisel veri yazılmayacaktır. (§4.7)

## R6 · Otonom tetik + API + UI (F6) — SCOPE §4.4–4.8, Kit §7
- R6.1 `inbound-email/` altına nesne oluştuğunda, `email_trigger` insan girdisi olmadan AgentCore'u `SINYAL_ISLE` ile ÇAĞIRACAKTIR. (§4.4)
- R6.2 E-posta işlenirken, gönderen/alıcı adresi, imza ve telefon numaraları agent'a GİTMEYECEK ve loglanmayacaktır. (KÇ5)
- R6.3 Gövde bir `Ham Metin (LLM Girdisi)` ile normalize eşleşirse, o sinyalin numarası KULLANILACAK; aksi halde `SG-2611-0xx` yeni sinyal `signals/` altına yazılacaktır. (§4.5, D6)
- R6.4 Aynı S3 nesnesi ikinci kez geldiğinde, sistem onu İŞLEMEYECEKTİR. (§4.4.5)
- R6.5 UI 4 ekranı (Uyarı, Etki, Seçenekler, Öneri ve onay) Türkçe ve Türkçe sayı biçimiyle GÖSTERECEK, hesap YAPMAYACAKTIR. (§4.8)
- R6.6 Kullanıcı Onayla'ya bastığında, karar kaydı `Onaylandı` OLACAKTIR; Reddet "yanlış alarm" ve Değiştir notu kaydedilecektir. (§4.8, §5.1)
- R6.7 API, paylaşılan anahtar başlığı olmayan istekleri REDDEDECEKTİR. (§4.8)

## R7 · Demo ve teslim (F7) — hackathon_kural_seti.md §7, SCOPE §6.1
- R7.1 `demo_reset` S3 durumunu temizleyecek, toplu tarama canlı sinyalleri (`DEMO_CANLI_SINYALLER`) hariç tutacaktır. (D17)
- R7.2 Kök README kurulum, deploy, hesap ID ve bölgeyi İÇERECEKTİR; mimari çizim `docs/mimari/` altında olacaktır.
