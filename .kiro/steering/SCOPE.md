---
inclusion: always
---

# NEXUS · SCOPE — Kiro için çerçeve ve orkestrasyon dokümanı

> **Amaç.** Kiro, NEXUS'u bu dosyayı çerçeve alarak geliştirir. Dosya beş şeyi tanımlar:
> 1. Hangi kaynak hangi öncelikle okunur?
> 2. Hangi proje kararları geçerlidir?
> 3. Bileşenler (md dokümanları, veri, agent'lar, bulut servisleri) nasıl bir araya gelir?
> 4. İş hangi sırayla yapılır?
> 5. Bir iş ne zaman "bitti" sayılır?
>
> **Kendi başına yeter.** `00_README_indeks.md`'ye dayanmaz. O dosya bilgi amaçlı bir indekstir ve **değiştirilmez**.
> **Sabitler:** D0 ("bugün") = **2026-11-25** (`Parametreler → AnalizTarihi`). Canlı demo senaryosu = **S1**. Tüm şirket, kişi ve rakamlar sentetiktir.

---

## 0. Kiro çalışma talimatı (her oturumda geçerli)

1. **Önce haritaya bak.** Bir işe başlamadan önce §3'teki bileşen haritasından hangi md'lerin geçerli olduğunu belirle. `fileMatch` dokümanları ilgili klasördeki bir dosya açılınca otomatik yüklenir. Yüklenmediyse dokümanı açıkça oku.
2. **Çelişkiyi hiyerarşiyle çöz** (§1). Hiyerarşi de çözmüyorsa dur ve kullanıcıya sor. Varsayım, sütun adı veya rakam uydurma.
3. **Fazları sırayla yürüt** (§6). Bir fazın "bitti" kriteri sağlanmadan sonrakine geçme. İki istisna var: kullanıcı açıkça isterse ya da §6.2'deki paralel şeritlerden biri çalışılıyorsa.
4. **Her fazın sonunda kısa bir rapor ver:** ne yapıldı, hangi testler çalıştı ve sonuçları, açık riskler, sıradaki adım.
5. **Kodu yazmadan önce kırmızı çizgileri (§2) kontrol et.** Bir talep bunlarla çelişiyorsa uygulamadan önce kullanıcıyı uyar.
6. **Bu dosyadaki kararları kendiliğinden değiştirme.** Değişiklik gerekiyorsa öner. Kullanıcı onaylarsa §5'e yeni bir karar satırı olarak ekle.
7. **AWS'de kaynak oluşturan, değiştiren veya silen komutlar** (deploy, S3 silme, SES kuralı, IAM rolü) için çalıştırmadan önce kullanıcıdan onay al.

---

## 1. Kaynak hiyerarşisi

| Öncelik | Kaynak | Rolü | Kiro'da nasıl yüklenir? |
|---|---|---|---|
| 1 | `hackathon-rules.md` (**esas**) + `hackathon_kural_seti.md` | **Sınır.** Bedrock, Strands/Nova Act, AgentCore'a deploy, sentetik veri, A1–A3 ajan kriterleri, teslimatlar. İkisi çelişirse `hackathon-rules.md` geçerlidir. | always |
| 2 | **`SCOPE.md`** (bu dosya) | Proje kararları, bulut mimarisi, fazlar, "bitti" tanımı. Kural md'leri hariç diğer tüm kaynakların üstündedir. | always |
| 3 | `docs/kaynak/Hackathon_Adimlar_Detay.docx` | İş akışı (ADIM 1–7) ve agent kapsamının hikâyesi | Gerektiğinde okunur |
| 4 | `nexus-data.md` | Veri kapsamı: sayfa, sütun, anahtar, formül. **Sütun adları birebir buradan alınır.** | always |
| 5 | `00_ortak_veri_semalari.md` | Agent'lar arası sözleşmeler (Pydantic). Alan adı veya tip çelişkisinde agent veri md'lerinin üstündedir. | fileMatch `src/**` |
| 6 | `00_…` – `05_…` agent md'leri (`*_kapsam_gorev.md`, `*_veri_kurallari.md`) | Her agent'ın rolü, görev adımları, tool'ları, kuralları, hata durumları ve kabul kriterleri | fileMatch (§3) |
| 7 | `docs/kaynak/NEXUS_Hackathon_Hazirlik_Kiti.pdf` | Demo akışı, 4 ekranın içeriği, jüri soruları, gerekçe tonu | Gerektiğinde okunur |
| 8 | `docs/kaynak/Welcome_Session.pdf` | Kural setinin orijinal kaynağı (yalnızca doğrulama için) | Gerektiğinde okunur |
| — | `00_README_indeks.md` | Bilgi amaçlı indeks. SCOPE ile çelişirse SCOPE geçerlidir. **Değiştirilmez.** | always (mevcut başlığıyla) |

**Veri dosyaları kaynak doküman değildir, veridir** (§4.6): `data/nexus_agent_input.xlsx` (GİRDİ) ve `tests/fixtures/nexus_answer_key.xlsx` (CEVAP ANAHTARI).

---

## 2. Kırmızı çizgiler (özet; ayrıntılar kural md'lerinde)

| # | Kural |
|---|---|
| KÇ1 | Tüm LLM çağrıları **yalnızca Amazon Bedrock** üzerinden yapılır. OpenAI, Anthropic API, Gemini, Ollama, yerel model veya başka bir sağlayıcının SDK'sı eklenmez. |
| KÇ2 | Agent'lar **Strands Agents** ile yazılır. Yeni bir framework veya servis önermeden önce §4.2'deki listeyle uyum kontrol edilir. |
| KÇ3 | Final akış **Amazon Bedrock AgentCore Runtime**'da çalışır ve **AgentCore Observability** açıktır. Yerelde çalıştırma yalnızca geliştirme ve test içindir, değerlendirmeye alınmaz. |
| KÇ4 | Kod hackathon sırasında **sıfırdan** yazılır. Hazır şablon veya eski repo kopyalanmaz. |
| KÇ5 | Yalnızca sentetik veri kullanılır. Gerçek kişisel veri (ad, TCKN, telefon, e-posta adresi, adres, imza) üretilmez, saklanmaz, loglanmaz, prompt'a konmaz. |
| KÇ6 | **Cevap anahtarı runtime'da asla açılmaz.** S3'e yüklenmez. Değerleri `src/` koduna, prompt'a veya few-shot'a girmez. Yalnızca `tests/` okur. |
| KÇ7 | **LLM sayı üretmez ve değiştirmez.** Sayılar deterministik tool'lardan gelir. Tek istisna Risk Agent'taki `DisKosulBileseni.puan`'dır (gerekçe ve kanıt zorunlu). |
| KÇ8 | Parametreler (ağırlık, eşik, kur, tampon) `Parametreler` sayfasından okunur, kodda sabit yazılmaz. Sütun adları `nexus-data.md`'den birebir alınır. |
| KÇ9 | **Karar insandadır.** Sistem sipariş vermez, ERP'ye yazmaz. Yalnızca gerekçeli öneri sunar. |
| KÇ10 | **Bilinmeyen değer `null` + uyarı** olarak döner. 0 veya tahminle doldurulmaz. |
| KÇ11 | Gizli bilgi koda gömülmez. Ortam değişkeni veya IAM rolü kullanılır. Bağımlılıkların sürümü sabitlenir. |
| KÇ12 | Kurulum, deploy, **AWS hesap ID'si ve bölge** repo kökündeki `README.md`'de belgelenir. Bu dosya Kiro'nun yazacağı kök README'dir. `.kiro/steering/00_README_indeks.md` farklı bir dosyadır ve ona dokunulmaz. |

---

## 3. Bileşen haritası

### 3.1 Bileşen → doküman → sözleşme → faz

| Bileşen | Klasör | Kapsam md | Veri md | Ürettiği sözleşme | Faz |
|---|---|---|---|---|---|
| Sözleşmeler | `src/contracts/` | — | `00_ortak_veri_semalari.md` | Tüm modeller | F1 |
| Veri erişimi | `src/data_access/` | — | `nexus-data.md` §1, §4, §8, §9 · `00_orkestrator_veri_kurallari.md` §1 | Yüklenmiş veri + `params` + D0 | F1 |
| Impact Agent | `src/agents/impact/` | `03_impact_agent_kapsam_gorev.md` | `03_impact_agent_veri_kurallari.md` | `ImpactOutput` | F2 |
| Risk Agent | `src/agents/risk/` | `02_risk_agent_kapsam_gorev.md` | `02_risk_agent_veri_kurallari.md` | `RiskOutput` | F2 (tool) / F3 (LLM) |
| Signal Agent | `src/agents/signal/` | `01_signal_agent_kapsam_gorev.md` | `01_signal_agent_veri_kurallari.md` | `SignalOutput` | F3 |
| Options Agent | `src/agents/options/` (`sourcing/`, `logistics/`) | `04_options_agent_kapsam_gorev.md` | `04_options_agent_veri_kurallari.md` | `OptionsOutput` | F4 |
| Decision Agent | `src/agents/decision/` | `05_decision_agent_kapsam_gorev.md` | `05_decision_agent_veri_kurallari.md` | `DecisionOutput` + karar kaydı taslağı | F4 |
| Orkestratör | `src/orchestrator/` | `00_orkestrator_kapsam_gorev.md` | `00_orkestrator_veri_kurallari.md` | `KararKaydi` | F5 |
| AgentCore giriş noktası | `src/app.py` | SCOPE §4.7 | — | — | F0 (iskelet) / F5 |
| E-posta tetikleyici | `src/triggers/email_trigger/` | SCOPE §4.4, §4.5 | — | Sinyal kaydı | F6 |
| UI arka ucu | `src/api/` | SCOPE §4.8 | — | — | F6 |
| UI | `ui/` | SCOPE §4.8 · Kit §7 | — | — | F6 |
| Altyapı | `infra/`, `scripts/` | SCOPE §4 | — | — | F0 / F6 |
| Testler | `tests/` | SCOPE §7 | Her agent veri md'sinin "Test eşlemesi" bölümü · ortak şema §7 | — | Her faz |

### 3.2 Repo yapısı

```
.kiro/
  steering/        SCOPE.md + 17 md (kural ×2, nexus-data, indeks, ortak şema, 00–05 ×2)
  specs/nexus-mvp/ requirements.md · design.md · tasks.md   ← Kiro üretir (§8.2)
  hooks/           ← Kiro üretir (§8.3)
config/            .env.example · email_kaynaklari.yaml   (gizli bilgi yok)
data/              nexus_agent_input.xlsx                  (GİRDİ, yerel geliştirme kopyası)
docs/kaynak/       Hackathon_Adimlar_Detay.docx · NEXUS_Hackathon_Hazirlik_Kiti.pdf · Welcome_Session.pdf
docs/mimari/       mimari çizim (F7)
infra/             altyapı kodu: S3, SES kuralı, Lambda'lar, IAM
scripts/           deploy · demo_reset · toplu_tarama
src/
  app.py           AgentCore Runtime giriş noktası
  common/          saf yardımcılar: gün indeksi, kur ve birim dönüşümü
  contracts/       schemas.py · json/
  data_access/     Excel okuma (yerel yol veya s3:// URI)
  orchestrator/
  agents/
    signal/  risk/  impact/  decision/      → her biri: agent.py · tools/ · prompts/
    options/  sourcing/ · logistics/ · agent.py
  triggers/email_trigger/
  api/
ui/
tests/
  fixtures/nexus_answer_key.xlsx
  contracts/  unit/<agent>/  e2e/
README.md          kurulum · deploy · hesap ID · bölge
pyproject.toml     (veya requirements.txt; sürümler sabit)
```

**Tool konumu (karar D11):** Her agent'ın tool'ları kendi klasöründe durur (`src/agents/<agent>/tools/`). Böylece o agent'ın steering md'leri `fileMatch` ile otomatik yüklenir. Her tool'un sahibi tek bir agent'tır. `src/common/` yalnızca hiçbir agent'a ait olmayan saf yardımcıları tutar.

---

## 4. Çalışma zamanı mimarisi (bulut)

### 4.1 Akış

```
Taşıyıcı e-postası ──► Amazon SES (gelen e-posta kuralı)
                          │ ham MIME
                          ▼
                 S3  inbound-email/  ◄──── yedek tetik: UI'dan veya CLI'dan .eml / metin yükleme
                          │ S3 olay bildirimi (ObjectCreated)
                          ▼
                 Lambda  email_trigger  ── kişisel veriyi temizler, sinyal kaydını üretir (§4.5)
                          │ InvokeAgentRuntime  {eylem: SINYAL_ISLE}
                          ▼
 ┌──────────── Amazon Bedrock AgentCore Runtime (tek uygulama, §4.7) ───────────┐
 │  Orkestratör (deterministik durum makinesi, LLM çağırmaz)                    │
 │    Signal ─► Risk(Olasılık) ∥ Impact ─► Risk(Puan, Kademe) ─► Options ─► Decision │
 │  Signal, Risk, Impact, Options, Decision = Strands agent'ı + Bedrock reasoning LLM │
 │  Veri katmanı: S3 input/nexus_agent_input.xlsx (salt okunur, akış başına bir kez) │
 └───────────────┬──────────────────────────────────────────────────────────────┘
                 │ Zarf'lı JSON çıktılar            AgentCore Observability (izler)
                 ▼
     S3  runs/ · registry/ · decisions/
                 ▲
  Lambda  api (Function URL) ◄────► UI (S3'te statik web, 4 ekran)
                 │ insan kararı ──► InvokeAgentRuntime {eylem: INSAN_KARARI}
                 ▼                   (karar kaydının durumunu yalnızca Orkestratör günceller)
```

**Orkestratör durum makinesi (MVP):**

```
BEKLE ─► SINYAL ─┬─ AYIKLA ──────────────► KAPAT (gerekçe loglanır)
                 ├─ eşleşme yok ─────────► IZLEME (uyarı)
                 └─ ANALIZ ─► RISK_OLASILIK ∥ ETKI ─► RISK_KADEME
                                 ├─ Yüksek (≥ EsikYuksek) ─► SECENEK ─► KARAR ─► ONAY_BEKLIYOR ─► KAYIT
                                 ├─ Orta   (≥ EsikOrta)   ─► SECENEK (hazırda tutulur) ─► UYARI
                                 └─ Düşük                 ─► IZLEME
herhangi bir adımda sözleşme hatası, zaman aşımı veya Bedrock hatası ─► HATA (kısmi sonuç "tamamlanamadı")
```

`WHAT_IF` durumu MVP'de **yazılmaz** (karar D7).

### 4.2 Servisler ve kurallarla ilişkisi

| Servis / araç | Rolü | Kurallar karşısındaki durumu |
|---|---|---|
| Amazon Bedrock | Tüm LLM çağrıları | İzinli (R2, R3) |
| Bedrock AgentCore **Runtime** | Orkestratör ve agent'ların deploy hedefi | İzinli, zorunlu temel bileşen (P1, rules §2) |
| Bedrock AgentCore **Observability** | Adım bazlı izler ve loglar | İzinli, temel bileşen |
| Strands Agents | Agent SDK'sı | İzinli (R3) |
| Kiro | Agentic geliştirme | İzinli |
| Amazon S3, Amazon SES, AWS Lambda, IAM, CloudWatch | Destek altyapısı: depolama, gelen e-posta, tetikleme, yetki, log | LLM veya agent servisi değildir, R2 ve R3 ile çelişmez. Mimari çizimde "destek servisleri" olarak gösterilir. |
| pandas, openpyxl, pydantic, PuLP, boto3 | Python kütüphaneleri | Servis değildir, izinli servis listesini değiştirmez |

Bu listenin dışında bir servis gerekirse önce kullanıcıya sorulur.

### 4.3 Model ve bölge

- **Model:** Hesapta erişimi açık **en güçlü reasoning modeli** seçilir. Seçim F0'da hesapta erişilebilen modeller ve inference profile'lar listelenerek yapılır. Model kimliği yalnızca `BEDROCK_MODEL_ID` ortam değişkeninden okunur, kodda sabit yazılmaz. Bütün agent'lar aynı değişkeni kullanır.
- **LLM ayarı:** Çıkarım ve sınıflandırma çağrılarında düşük sıcaklık kullanılır (0–0,2). LLM çıktısı yalnızca LLM sınır modellerine (`SignalLLMCikarimi`, `DisKosulBileseni`, `DecisionMetinLLM`) Strands'in yapılandırılmış çıktı özelliğiyle yazılır.
- **Bölge:** SES gelen e-posta, AgentCore Runtime ve seçilen model **aynı bölgede** bulunmalıdır. Öneri `us-east-1`'dir; F0'da hesapta doğrulanır. Seçilen bölge `AWS_REGION` ortam değişkeninde ve kök `README.md`'de yazılır.

### 4.4 Otonom tetik (SES) — A2

- SES ile gelen e-posta almak için **doğrulanmış bir alan adı ve MX kaydı** gerekir. F0'da bunun mümkün olup olmadığı kontrol edilir.
- Alma kuralı: alıcı adresi (ör. `signals@<alan-adı>`) → S3 eylemi, `inbound-email/` önekine yazar.
- `inbound-email/` önekindeki `ObjectCreated` olayı `email_trigger` Lambda'sını tetikler. **Tetik zinciri S3'ten başlar.** SES hazır değilse aynı önekine yükleme yapılarak (UI'daki "e-posta gönder (yedek)" düğmesi veya CLI) aynı akış çalışır. Akış değişmez, yalnızca e-postanın S3'e nasıl geldiği değişir.
- `email_trigger` Lambda'sının görevleri:
  1. MIME'ı ayrıştırır (Python `email` modülü). Gövde metnini ve `Date` başlığını alır.
  2. **Kişisel veriyi temizler:** gönderen ve alıcı adresleri, imza bloğu ve telefon numaraları agent'a gitmez ve loglanmaz (KÇ5).
  3. Sinyal kaydını üretir (§4.5).
  4. AgentCore'u çağırır: `InvokeAgentRuntime`, payload `{"eylem":"SINYAL_ISLE","sinyal_no":…,"kaynak":"EMAIL"}`.
  5. **Idempotent'tir:** aynı S3 nesnesi ikinci kez işlenmez (`registry/` kontrolü).
- `inbound-email/` için S3 yaşam döngüsü kuralı 1 gündür (ham MIME kişisel veri içerebilir).

### 4.5 E-postadan sinyal kaydına (karar D6)

1. **Önce mevcut sinyallerle eşleştir.** Temizlenmiş gövde normalize edilir (boşluk, satır sonu, büyük/küçük harf). Sonra girdi dosyasındaki `Risk_Sinyalleri.Ham Metin (LLM Girdisi)` ile karşılaştırılır. Birebir eşleşirse o satırın `Sinyal No`'su ve meta verisi (`Kaynak Kodu`, `Kaynak Taban Güvenilirlik`, `Doğrulandı mı?`, `Yayın Zamanı`, `Tespit Zamanı`, `Dil`) kullanılır.
   → **Canlı demoda SG-2611-001'in metni e-postayla gönderilir.** Meta veri Excel'den geldiği için S1 rakamları (güvenilirlik 5, olasılık 4,4 …) birebir korunur.
2. **Eşleşmezse yeni sinyal açılır:**
   - `Sinyal No`: girdideki ve `registry/` içindeki en büyük `SG-2611-0xx` + 1 (ilk yeni numara `SG-2611-019`).
   - `Kaynak Kodu`: `config/email_kaynaklari.yaml` dosyasındaki gönderen alan adı → `KYxx` eşlemesinden alınır. Eşleme yoksa `null` + `ESLESME_YOK` uyarısı verilir; Risk bu durumda eksik bileşen bayrağıyla çalışır ve sinyal onaya sunulmaz.
   - `Doğrulandı mı?` = `"Hayır"`. `Yayın Zamanı` = e-postanın `Date` başlığı. `Tespit Zamanı` = S3 nesnesinin oluşma zamanı.
   - Kayıt `signals/<Sinyal No>.json`'a yazılır. **Girdi Excel'i değiştirilmez.**
3. Runtime'daki sinyal kümesi = girdi Excel'indeki sinyaller + `signals/` altındaki yeni sinyaller.

### 4.6 Veri ve durum (S3)

Kova adı: `nexus-<hesap-id>-<bölge>` (ortam değişkeni `NEXUS_BUCKET`).

| Önek | İçerik | Kural |
|---|---|---|
| `input/nexus_agent_input.xlsx` | GİRDİ dosyası | Salt okunur, deploy sırasında yüklenir. Veri katmanı `NEXUS_INPUT_URI`'den okur (yerelde `data/…`, bulutta `s3://…`). |
| `inbound-email/` | SES'in yazdığı ham MIME | 1 günlük yaşam döngüsü, kişisel veri |
| `signals/<Sinyal No>.json` | E-postadan türetilen yeni sinyaller | §4.5 |
| `runs/<run_id>/<agent>.json` | Her agent'ın Zarf'lı çıktısı | UI bunları okur |
| `registry/risks.json` | Risk kayıt defteri: (sevkiyat, malzeme) → `risk_no`, bağlı sinyaller, son `run_id` | Karar D8 |
| `registry/processed.json` | İşlenmiş S3 nesneleri ve sinyaller | Idempotency |
| `decisions/<Olay No>.json` | `KararKaydi` | §5.1 eşlemesi |
| `exports/Karar_Kaydi.xlsx` | Cevap anahtarı formatında dışa aktarım | Opsiyonel, sunum için |

- **Cevap anahtarı S3'e yüklenmez** (KÇ6).
- Hackathon kapsamında tek yazıcı vardır, eşzamanlılık kilidi gerekmez.

### 4.7 AgentCore paketleme (karar D2: tek Runtime)

- `src/app.py` dosyası `BedrockAgentCoreApp` giriş noktasıdır. `eylem` alanına göre çalışır:
  - `SINYAL_ISLE`: tek sinyal, uçtan uca akış
  - `TOPLU_TARAMA`: girdideki sinyallerin hepsi veya seçilenler
  - `INSAN_KARARI`: Onayla, Reddet veya Değiştir → karar kaydı
- Orkestratör agent'ları aynı süreç içinde çağırır. Her agent'ın **aynı zamanda** saf bir Python arayüzü vardır: `run(girdi) -> *Output`. Böylece her agent ayrı test edilebilir ve ayrı çağrılabilir (O8). Gerekirse ileride ayrı Runtime'lara bölünebilir.
- Deploy için AgentCore starter toolkit (`agentcore configure` / `agentcore launch`) kullanılır. AgentCore Runtime ARM64 konteyner çalıştırır; bağımlılıklar buna uygun seçilir (karar D15).
- IAM rolünün izinleri: Bedrock `InvokeModel`, `NEXUS_BUCKET` için okuma ve yazma, CloudWatch ve X-Ray.
- **Observability:** AgentCore Observability açıktır. Her orkestratör adımı ayrı bir span'dir; girdi özeti, çıktı özeti, süre ve uyarılar bu span'e yazılır. Kişisel veri yazılmaz. `run_id` AgentCore oturum kimliği olarak da kullanılır.

### 4.8 UI (karar D14)

- **UI'ı Kiro yazar.** Kısıtlar:
  - AWS'de çalışır: statik web S3'te durur (gerekirse CloudFront eklenir).
  - Arka uç `api` Lambda'sıdır (Function URL). Erişim ortam değişkeninde tutulan basit bir paylaşılan anahtarla korunur; bu hackathon için yeterlidir. AgentCore'u yalnızca Lambda IAM ile çağırır.
  - **UI hesap yapmaz.** Rakamlar yalnızca `runs/` altındaki agent çıktılarından okunur.
  - Dil Türkçedir, sayılar Türkçe biçimdedir (`2.741.018 TL`, `9,89 gün`, `04.12 21:16`).
  - Ekran 1 düzenli aralıklarla yenilenir. E-posta gelince yeni risk insan girdisi olmadan ekranda belirir (otonominin gösterimi).
- **Ekranlar ve içerikleri** (Kit §7). Görünüm sade olabilir, içerik eksik olamaz:

| Ekran | Kaynak çıktı | İçerik |
|---|---|---|
| 1 · Uyarı paneli | `SignalOutput` + `RiskOutput` | Gelen sinyal metni, çıkarılan alanlar (sevkiyat, malzeme, gecikme, ipucu), risk kartı (Olasılık × Etki = Puan, Kademe, açıklama), izlenen riskler listesi |
| 2 · Etki | `ImpactOutput` | 4 kutu (stok bitişi, malzemenin kullanılabilir olduğu tarih, duruş, aksiyonsuz maliyet) ve zaman çizelgesi |
| 3 · Seçenekler | `OptionsOutput` + `DecisionOutput` | Stratejiler yan yana: duruş, toplam maliyet, CO2, risk, skor, sıra, "ÖNERİLEN" |
| 4 · Öneri ve onay | `DecisionOutput` | Tek kart: öneri, gerekçe (LLM), hiçbir şey yapmamanın maliyeti, tasarruf, **Onayla / Reddet / Değiştir**. Reddet için "yanlış alarm" işareti, Değiştir için not alanı. **What-if bağlantısı yok** (D7). |

---

## 5. Proje kararları (geçerli olanlar)

| # | Karar | Gerekçe ve etkisi |
|---|---|---|
| K1 | Risk ve Impact **iki ayrı agent'tır**. Runtime'da Risk (Olasılık) ile Impact paralel çalışır, Risk Puanı ve Kademe en son hesaplanır. Ekranlarda ve anlatımda docx sırası korunur. | Etki (1–5), Impact'in aksiyonsuz maliyetinden türetilir. |
| K2 | Docx'teki ADIM 2–3 (kullanılabilir tarih, stok kapsama) **Impact Agent**'ın işidir. | nexus-data.md #3, Kit §5 |
| K3 | Options **tek agent, iki alt modüldür** (Sourcing, Logistics). | Docx ADIM 6 a/b/c |
| K4 | **Notification Agent yoktur.** Öneri kartı ve karar kaydı taslağı Decision Agent'ta, karar durumunun güncellenmesi Orkestratör'dedir. `KPI_Panel` sunum malzemesidir. | `nexus-data.md` §2'deki #6 satırı **geçersizdir**. |
| K5 | Orkestratör **deterministik bir durum makinesidir** ve LLM çağırmaz. | İzlenebilirlik. Reasoning (A1) agent'ların içindedir. |
| K6 | Her agent Bedrock üzerindeki bir reasoning LLM ile çalışan bir **Strands agent'ıdır**. LLM planlar, yorumlar, doğrular, gerekçelendirir ve tool çağırır. **Sayıları yalnızca tool'lar üretir.** LLM'in yazabildiği tek yapılar LLM sınır modelleridir (ortak şema §6). | A1 ile "hesabı LLM yapmıyor" ilkesinin uzlaşısı |
| D1 | AgentCore'un temel bileşen kullanımı **zorunludur**: Runtime + Observability. | `hackathon-rules.md` esas alınır. `hackathon_kural_seti.md`'deki R4'ün "ÖNERİLİR" ifadesi geçersizdir. |
| D2 | Tek bir AgentCore Runtime vardır; Orkestratör ve 5 agent aynı pakettedir. Agent'lar ayrı modül olarak ayrı test edilebilir. | Demo riski düşük, kurulum basit |
| D3 | Otonom tetik zinciri: SES → S3 → Lambda → AgentCore. Yedeği S3'e manuel yüklemedir. | A2; §4.4 |
| D4 | Girdi Excel'i, çalışma durumu ve karar kaydı S3'tedir. Cevap anahtarı yalnızca repoda, `tests/fixtures/` altındadır. | §4.6 |
| D5 | Model, erişilebilen en güçlü Bedrock reasoning modelidir ve `BEDROCK_MODEL_ID`'den okunur. | §4.3 |
| D6 | E-postadan sinyal kaydı önce eşleşmeyle, olmazsa yeni kayıtla üretilir. | §4.5; demo rakamları korunur |
| D7 | **What-if, MVP ve demo kapsamının dışındadır.** Agent md'lerindeki what-if kabul kriterleri askıya alınır. Kod `WhatIfGun`'u yine `Parametreler`'den okur; değeri 0 olduğu için etkisizdir. Orkestratörde `WHAT_IF` durumu yazılmaz, UI'da what-if bağlantısı yoktur. Demo, Kit §1'deki 1–5. adımlardan oluşur. Aynı sevkiyata ikinci sinyal gelirse mevcut `risk_no`'ya **bağlanır**; yeniden hesaplama F8'e (opsiyonel) bırakılır. | Kullanıcı kararı. Cevap anahtarında +7 gün sonrası öneri bulunmuyor. |
| D8 | `risk_no`, Orkestratör'ün kayıt defterinde `R-01`'den başlayarak, (sevkiyat, malzeme) anahtarına göre sırayla atanır. Cevap anahtarındaki `R-xx` ile eşitlik beklenmez. Testler riskleri **ilgili sevkiyat ve malzeme** üzerinden eşleştirir. | Ortak şema §7'deki "kimlik birebir" kuralı `risk_no` ve `olay_no` için bu şekilde esnetilir. Demoda S1'in numarası R-01 olmayabilir. |
| D9 | Yeni karar kayıtları `NXS-26-025`'ten başlar. Cevap anahtarında `NXS-26-001…024` ile `NXS-26-S1…S3` vardır. Testler numarayı değil içerik alanlarını karşılaştırır. | `NXS-26-S1` şema desenine uymuyor. |
| D10 | `KararKaydi` şeması §5.1'deki alanlarla genişletilir. Excel eşlemesi §5.1'dedir. F1'de bu değişiklik **önce** `00_ortak_veri_semalari.md` §5 ve §8'e işlenir, `SEMA_VERSIYONU = "1.1"` yapılır, sonra kod yazılır. | Ortak şema G12; §8'de bekleyen iş kapanır. |
| D11 | Tool'lar `src/agents/<agent>/tools/` altında durur. | `fileMatch` otomatik çalışır (§3.2). |
| D12 | `Senaryo` girdi dosyasında yoktur, cevap sütunudur. `Zarf.senaryo` runtime'da `null` kalabilir ve test edilmez. | What-if kapsam dışında olduğu için ihtiyaç yok |
| D13 | **"Bitti" tanımı:** S1, e-postadan onay ekranına kadar **bulutta** uçtan uca çalışır ve S1 rakamları §7.2 ile uyumludur. S2, S3, izleme ve gürültü sinyalleri toplu taramada çalışmalıdır, ancak S1 testleri geçmeden bunlara zaman harcanmaz. | Kit §8 |
| D14 | UI'ı Kiro yazar; kısıtlar §4.8'dedir. | Kullanıcı kararı |
| D15 | MILP için PuLP (CBC) kullanılır. ARM64'te çözücü sorun çıkarırsa `scipy.optimize.milp` (HiGHS) yedektir. İkisi de çalışmazsa `MILP_YAPILAMADI` uyarısı verilir ve ÇKKV sonucu sunulmaya devam eder. | Decision hata tablosu |
| D16 | Gerekçe ve UI dili Türkçedir. Karar kaydında kişi adı yerine rol yazılır (ör. "Satınalmacı"). | KÇ5, Kit §8 |
| D17 | Demo hazırlığında `scripts/demo_reset.py` S3'teki durumu temizler. Ardından toplu tarama, canlı demo sinyalleri hariç tutularak çalıştırılır (`DEMO_CANLI_SINYALLER=SG-2611-001,SG-2611-002`). Böylece Ekran 1'deki izlenen riskler listesi dolu gelir, S1 ise canlı e-postayla başlar. | Demo akışı |

### 5.1 Karar kaydı: şema (v1.1) ↔ `Karar_Kaydi` sayfası eşlemesi

Cevap anahtarındaki `Karar_Kaydi` sayfasının 21 sütunu (başlık 1. satırda) aşağıda eşlenmiştir. "Yeni" işaretli alanlar `KararKaydi` modeline v1.1 ile eklenir.

| Excel sütunu | Şema alanı | Kaynak / dönüşüm |
|---|---|---|
| `Olay No` | `olay_no` | D9: `NXS-26-025`'ten başlayarak sırayla |
| `Tarih` | `tarih` (yeni, `date`) | Zarf `d0` |
| `Kuruluş Kodu` | `kurulus_kodu` (yeni) | Impact zincirindeki `Malzemeler.Kuruluş Kodu` |
| `Olay Tipi` | `olay_tipi` (yeni) | Enum: `Tedarik`, `Lojistik`, `Birleşik (Tedarik + Lojistik)`. Decision LLM'i gerekçeli sınıflandırır; serbest metin olduğu için sayı içermez. |
| `Olay Özeti` | `olay_ozeti` (yeni) | Decision LLM'i tek cümle yazar. İçindeki rakamlar gerekçe rakam testine tabidir. |
| `Sinyal Yayın Zamanı` | `sinyal_yayin_zamani` (yeni) | İlk bağlı sinyalin `Yayın Zamanı` değeri (§4.5) |
| `Tespit Zamanı` | `sinyal_tespit_zamani` | İlk bağlı sinyalin `Tespit Zamanı` değeri |
| `Öneri Hazır Zamanı` | `oneri_zamani` | `DecisionOutput.bitis_zamani` |
| `Onay/Red Zamanı` | `karar_zamani` | `InsanKarari.karar_zamani`; karar bekleniyorsa boş |
| `Önerilen Aksiyon` | `onerilen_aksiyon` (yeni) | ÖNERİLEN stratejinin adı (`OptionsOutput`). Kodu ayrıca `onerilen_strateji_kodu` alanında tutulur. |
| `Karar` | `karar` | `KararDurumu`. Decision kaydı `Onay Bekliyor` olarak açar, Orkestratör günceller. |
| `Yanlış Alarm mı?` | `yanlis_alarm_mi` (yeni, bool → `Evet`/`Hayır`) | Varsayılan `Hayır`. Reddet seçilip "yanlış alarm" işaretlenirse `Evet`. Bunun için `InsanKarari`'na `yanlis_alarm: bool = False` alanı eklenir. |
| `Risk Gerçekleşmeden Aksiyon mu?` | `risk_gerceklesmeden_aksiyon` (yeni, bool) | `oneri_zamani` < Impact'in hesapladığı tükenme anı ise `Evet` (deterministik) |
| `Aksiyonsuz Tahmini Maliyet (TRY)` | `aksiyonsuz_maliyet_try` | `ImpactOutput` |
| `Aksiyon Maliyeti (TRY)` | `onerilen_maliyet_try` | `DecisionOutput` |
| `Net Tasarruf (TRY)` | `tasarruf_try` | aksiyonsuz maliyet − önerilen maliyet |
| `Önlenen Duruş (gün)` | `onlenen_durus_gun` (yeni) | Impact'teki duruş günü − önerilen stratejinin simülasyondaki duruşu |
| `Tespit Süresi (saat)` | `tespit_suresi_dk` | (tespit − yayın) **dakika** cinsinden tutulur, Excel'e **÷ 60** ile saat olarak yazılır |
| `Öneri Hazırlama Süresi (dk)` | `oneri_suresi_dk` | (öneri − tespit), dakika; Excel'e olduğu gibi yazılır |
| `Onay Süresi (saat)` | `onay_suresi_dk` | (karar − öneri), dakika; Excel'e **÷ 60** ile saat olarak yazılır |
| `Kullanıcı Geri Bildirimi` | `kullanici_geri_bildirimi` (yeni) | Onay ekranındaki not veya `revize_notu`. Karar bekleniyorsa `"Yetkili onayı bekleniyor."` |

**S1 kaydının testi** (cevap anahtarındaki `NXS-26-S1` satırıyla karşılaştırılır):
- `kurulus_kodu = SAGLIK`
- `olay_tipi` anlamsal olarak `Birleşik (Tedarik + Lojistik)`
- `karar = Onay Bekliyor`
- Aksiyonsuz maliyet **2.741.018**, aksiyon maliyeti **109.567**, tasarruf **2.631.451** (±1 TL)
- Önlenen duruş **5,11** (±0,01)
- `risk_gerceklesmeden_aksiyon = Evet`, `yanlis_alarm_mi = Hayır`

Zaman damgaları ve süreler çalışma anına bağlı olduğu için **test edilmez**.

---

## 6. Geliştirme fazları

### 6.1 Fazlar ve "bitti" kriterleri

| Faz | Kapsam | Okunacak md'ler | "Bitti" kriteri |
|---|---|---|---|
| **F0 · Ortam ve yürüyen iskelet** | Repo yapısı (§3.2), sabit sürümlü bağımlılıklar, `config/.env.example`. AWS'de: bölge doğrulaması (SES gelen e-posta, AgentCore, model), erişilebilen modellerin listelenmesi ve `BEDROCK_MODEL_ID` seçimi, S3 kovası, `input/` yüklemesi, SES alan adı kontrolü. Tek bir Bedrock çağrısı yapan **iskelet AgentCore Runtime deploy'u**. | kural md'leri, SCOPE §4 | Buluttan çağrılan Runtime, Bedrock'tan cevap döner. Hesap ID'si, bölge ve model kök `README.md`'de yazılıdır. SES'in hazır olup olmadığı raporlanır. |
| **F1 · Sözleşmeler ve veri katmanı** | `src/contracts/schemas.py` (ortak şemadan birebir, D10 genişletmesiyle), JSON Schema dışa aktarımı. `src/data_access/`: tek yükleme, `PO No` string olarak, `"-"` → `None`, `00_Rehber` atılır, `params` ve D0 hazırlanır, yerel yol veya `s3://` desteklenir. `tests/` için cevap anahtarı okuyucuları (başlık satırları nexus-data.md §7'ye göre). | `00_ortak_veri_semalari.md`, `nexus-data.md`, `00_orkestrator_veri_kurallari.md` | Tüm modeller import edilir ve örnek S1 JSON'ları doğrulanır. Veri katmanı 15 sayfayı yükler. **Koruma testi** geçer (§7.1). Ortak şema md'si v1.1'e güncellenmiştir. |
| **F2 · Impact + Risk tool'ları** | Impact tool'ları I1–I13 ve Strands sarmalayıcısı (kayıt seçimi ve tutarlılık için LLM). Risk'in deterministik tool'ları (sinyal, performans, finansal, olasılık, puan, kademe). | `03_*`, `02_*` | S1 Impact değerleri §7.2 ile tolerans içinde uyumludur. Risk tool'ları sabit bir dış koşul girdisiyle doğru olasılık, puan ve kademeyi üretir. |
| **F3 · Signal + Risk LLM'i** | Signal: gürültü filtresi, LLM çıkarımı (`SignalLLMCikarimi`), eşleştirme tool'ları, güvenilirlik, gruplama. Risk: `DisKosulBileseni` (LLM), taraf seçimi, açıklama. | `01_*`, `02_*` | SG-2611-001 → `SV-26-1184`, `MT100054`, 8 gün, Mersin ipucu. Gürültü sinyalleri `AYIKLA` olur. S1 için Olasılık **4,4** × Etki **5** = **22 → Yüksek**. |
| **F4 · Options + Decision** | Sourcing ve Logistics tool'ları, C1–C6 kısıtları, hibrit miktar, 6 strateji. Decision: gün gün simülasyon, toplam maliyet, ÇKKV, sıralama, MILP (D15), LLM gerekçesi, gerekçe rakam testi, öneri kartı, karar kaydı taslağı. | `04_*`, `05_*` | S1'de 6 strateji vardır ve `Strateji_Karsilastirma` 2–7. satırlarla (duruş, toplam maliyet, sıra) tolerans içinde uyumludur. ÖNERİLEN = S1-HIB, **109.567 TL**, duruş 0. MILP amacı **108.745**. Gerekçe rakam testi geçer. |
| **F5 · Orkestratör + AgentCore** | Durum makinesi (§4.1, `WHAT_IF` yok), sözleşme doğrulaması, kademe kapısı, risk kayıt defteri, S3'e yazma, `INSAN_KARARI`. `src/app.py` eylemleri. Deploy ve Observability. | `00_orkestrator_*` | Buluttan `SINYAL_ISLE` SG-2611-001 çalıştırılınca S3'te 5 agent çıktısı ve `Onay Bekliyor` durumunda bir karar kaydı oluşur. Gürültü sinyali `KAPAT` olur. İzleme sinyalleri Orta veya Düşük kademede biter. Adım izleri Observability'de görünür. |
| **F6 · Otonom tetik + API + UI** | `email_trigger` Lambda'sı, SES kuralı (veya yedek tetik), `api` Lambda'sı, UI'daki 4 ekran (§4.8). | SCOPE §4.4–4.8, Kit §7 | E-posta (veya S3'e yükleme), insan girdisi olmadan Ekran 1'e düşer. Ekran 4'te Onayla'ya basılınca karar kaydı `Onaylandı` olur. Rakamlar Excel'le birebir aynıdır. |
| **F7 · Demo ve teslim** | `demo_reset`, prova (≤ 5 dk), her ekranın ekran görüntüsü ve 1 dakikalık video, mimari çizim (servislerle birlikte, `docs/mimari/`), kök `README.md` (kurulum, deploy, hesap ID, bölge), kodun zip'i veya GitHub linki. | kural md'leri §5/§8 | `hackathon_kural_seti.md` §7'deki son kontrol listesinin tamamı işaretlenmiştir. |
| F8 · Opsiyonel | S2/S3 kabul testleri, aynı sevkiyata gelen ikinci sinyalde yeniden hesaplama, what-if | ilgili agent md'leri | Yalnızca F7 bittikten sonra yapılır |

### 6.2 Paralel şeritler (takım çalışıyorsa)

Sözleşmeler (F1) sabitlendikten sonra şu şeritler birbirini beklemeden ilerleyebilir:

| Şerit | İçerik | Bağımlılık |
|---|---|---|
| A | F2 Impact → Risk tool'ları → F3 Risk LLM'i | F1 |
| B | F3 Signal | F1 |
| C | F4 Options → Decision. Testlerdeki girdi fixture'ları cevap anahtarından kurulur. | F1 |
| D | Altyapı: SES, `email_trigger` ve `api` Lambda'ları, UI iskeleti (fixture JSON ile) | F0 |

Şeritler F5'te birleşir. Her şerit ayrı bir Kiro oturumunda, kendi klasöründe çalışır.

### 6.3 Zaman daralırsa kesme sırası

Final sunumlar **17:30**'da başlıyor; teslim e-postası sunumdan önce gönderilir. Zaman yetmezse işler şu sırayla kesilir:

1. F8
2. S2/S3 testleri
3. MILP (`MILP_YAPILAMADI` uyarısıyla ÇKKV sürer)
4. SES (yedek tetik olarak S3'e yükleme kullanılır)
5. UI'ın görsel cilası

**Hiçbir koşulda kesilmeyecekler:** AgentCore'a deploy, Bedrock LLM'i, S1 rakamları, insan onayı, kök `README.md` (hesap ID ve bölge).

---

## 7. Test stratejisi

### 7.1 Genel

- Testler `pytest` ile yazılır ve şu klasörlere ayrılır: `tests/contracts/`, `tests/unit/<agent>/`, `tests/e2e/`.
- **Beklenen değerler yalnızca cevap anahtarından okunur.** Okuyucular `tests/` içindedir ve başlık satırlarına uyar (nexus-data.md §7; `Formuller` için `header=3`, `Agent_Haritasi`, `Veri_Kontrolleri` ve `Veri_Sozlugu` için `header=2`, `KPI_Panel` için 4. satır).
- **Toleranslar** ortak şema §7'dedir: gün ±0,01 · TRY ±1 · kg ±0,5 · olasılık ±0,01 · normalize skor ±0,001. `risk_no` ve `olay_no` için D8 ve D9 geçerlidir.
- **LLM testleri** `@pytest.mark.llm` ile işaretlenir; bunlar Bedrock gerektirir ve yavaştır. Deterministik testler ağ olmadan çalışır. Bunun için LLM sınır modeli girdileri fixture olarak verilir (ör. elle doldurulmuş bir `SignalLLMCikarimi`).
- Alt akıştaki agent'ların testleri, üst akış çıktısını cevap anahtarından kurulan fixture'larla alabilir. Bu yalnızca testlerde yapılır, runtime'da yapılmaz.
- **Koruma testi (zorunlu):** `src/` altında `nexus_answer_key` referansı bulunmamalıdır. Bilinen S1 cevap sabitleri de (ör. `2741018`, `109567`, `108745`, `2291018`) sabit değer olarak geçmemelidir. Ayrıca Bedrock dışı LLM SDK'larına ait import'lar (`openai`, `anthropic`, `google.generativeai`, `ollama`) bulunmamalıdır.
- LLM'in ürettiği bir bileşen (ör. dış koşul puanı) cevap anahtarıyla uyuşmazsa prompt ve kanıt bağlamı iyileştirilir. **Beklenen değer prompt'a yazılmaz** (R-K7, S1-K7).

### 7.2 S1 kabul tablosu (yalnızca test beklentisi)

> ⚠️ Bu tablo Kiro'nun test yazması içindir. Değerleri agent prompt'una, few-shot örneğine veya `src/` koduna kopyalama (KÇ6).

| Agent | Kontrol | Beklenen |
|---|---|---|
| Signal | SG-2611-001 | `SV-26-1184`, `MT100054`, gecikme **8 gün**, ipucu "Mersin'e liman değişikliği mümkün". SG-2611-002 aynı riske bağlanır. |
| Impact | Kullanılabilir tarih | ETA 05.12 + 1 gümrük + 1 iç nakliye + 3 kalite = **10.12 (15. gün)** |
| Impact | Tüketim ve kapsama | **60,69 kg/gün**, 600 kg serbest stok → **9,89 gün**, tükenme **04.12 21:16** |
| Impact | Duruş ve maliyet | **5,11 gün** · duruş maliyeti **2.291.018 TL** · ceza **450.000 TL** (4 sipariş) · aksiyonsuz maliyet **2.741.018 TL** · Etki puanı **5** |
| Risk | Puan | Olasılık **4,4** × Etki **5** = **22 → Yüksek** |
| Options | Seçenekler | **6 strateji** · D-SG-01'den transfer edilebilir **260 kg** · TD5012: hazır **1.500 kg**, MOQ **250 kg**, Ruhsatta Kayıtlı · Şanghay → İstanbul uçak **2 gün, 4,60 USD/kg** · hava bileşeni **8. gün** gelir · hibrit miktar **250 kg** · Mersin COD kısıtı geçer |
| Decision | Öneri | **Depodan 260 kg + Zhejiang'dan uçakla 250 kg** (S1-HIB), duruş **0**, toplam **109.567 TL** (MILP amacı 108.745 + stok taşıma 823), tasarruf **2.631.451 TL** |
| Decision | Sıralama | Hiçbir şey yapma 5,11 g / 2.741.018 · Sadece transfer 0,83 g / 554.863 · Kısmi uçak 0 / 137.187 · Tamamı uçak 0 / 350.075 · Mersin 4,11 g / 2.345.514 · **Hibrit 0 / 109.567 → ÖNERİLEN** |
| Orkestratör | Akış | Gürültü sinyalleri (SG-2611-013…017, SG-2610-*, `H` ekliler) onaya ulaşmaz. İzleme sinyalleri Orta veya Düşük kademede biter. |

---

## 8. Kiro çalışma modeli

### 8.1 Steering

- **Her zaman yüklenenler:** `SCOPE.md`, `hackathon-rules.md`, `hackathon_kural_seti.md` (başlık bilgisi yok, Kiro varsayılan olarak her zaman yükler), `nexus-data.md`, `00_README_indeks.md`.
- **`fileMatch` ile yüklenenler:**

| Doküman | Desen |
|---|---|
| Ortak şema | `src/**` |
| Orkestratör md'leri | `src/orchestrator/**` |
| Signal md'leri | `src/agents/signal/**` |
| Risk md'leri | `src/agents/risk/**` |
| Impact md'leri | `src/agents/impact/**` |
| Options md'leri | `src/agents/options/**` |
| Decision md'leri | `src/agents/decision/**` |

- `tests/unit/<agent>/` veya `infra/` altında çalışırken ilgili agent md'si otomatik gelmez. O durumda doküman açıkça okunur.

### 8.2 Spec

- Tek bir spec kullanılır: `.kiro/specs/nexus-mvp/`.
  - **requirements.md:** §6.1'deki "bitti" kriterleri ve §7.2 kabul tablosu, EARS biçiminde gereksinimlere çevrilir. Her gereksinim kaynak md'ye ve bölüme atıf yapar.
  - **design.md:** §4 mimarisi, §3 bileşen haritası ve §5 kararları. Yeni bir karar varsa işaretlenir ve kullanıcıya sorulur.
  - **tasks.md:** Görevler fazlara (F0–F7) göre gruplanır. Her görevde hangi md'nin okunacağı ve görevin "bitti" testi yazar. F8 görevleri "opsiyonel" olarak işaretlenir.
- Kiro görevleri sırayla yürütür ve her fazın sonunda §0.4'teki raporu verir.

### 8.3 Önerilen hook'lar

1. **Sözleşme testi:** `src/contracts/**` kaydedilince `pytest tests/contracts -q` çalışır.
2. **Agent birim testi:** `src/agents/<agent>/**` kaydedilince o agent'ın LLM'siz testleri çalışır (`pytest tests/unit/<agent> -m "not llm" -q`).
3. **Kural denetimi** (manuel tetiklenir): değişikliklerde Bedrock dışı LLM SDK'sı, cevap anahtarı referansı, sabit yazılmış parametre veya S1 cevap sabiti ve kişisel veri aranır. Bulgular raporlanır.

---

## 9. F0'da doğrulanacak riskler

| Risk | Kontrol | Yedek plan |
|---|---|---|
| SES gelen e-posta bölgesi ve doğrulanmış alan adı / MX kaydı | Bölge desteği ve alan adı durumu kontrol edilir | S3'e yüklemeyle tetik (D3) |
| Seçilen bölgede model erişimi | Erişilebilen modeller ve inference profile'lar listelenir | Bir alt model; aynı ortam değişkeni |
| Hackathon hesabının izinleri (IAM rolü oluşturma, AgentCore deploy için CodeBuild) | Deneme deploy'u (F0 iskeleti) | Mentörden yetki talep edilir |
| AgentCore ARM64 ortamında PuLP/CBC çözücüsü | F4'te MILP testinin Runtime içinde çalıştırılması | D15 |
| Dosya adlarındaki Unicode karakterler (`İ`, boşluk) | Dosyalar ASCII adlarla repoya konur | — |
