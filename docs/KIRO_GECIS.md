# NEXUS · Kiro'ya geçiş rehberi

> Bu dosya steering'e **konmaz**. Senin için bir kullanım kılavuzudur: repoyu kurma, Kiro'yu başlatma ve fazları yürütme.

---

## 1. Repoyu hazırla (≈10 dk)

Space'teki dosyaları indirip aşağıdaki gibi yerleştir. Excel ve PDF dosyalarının adındaki `İ`, boşluk ve `–` karakterleri ASCII'ye çevrilir.

```bash
mkdir nexus && cd nexus && git init
mkdir -p .kiro/steering data tests/fixtures docs/kaynak config

# Steering (18 md)
cp SCOPE.md hackathon-rules.md hackathon_kural_seti.md nexus-data.md 00_README_indeks.md \
   00_ortak_veri_semalari.md 00_orkestrator_kapsam_gorev.md 00_orkestrator_veri_kurallari.md \
   01_signal_agent_*.md 02_risk_agent_*.md 03_impact_agent_*.md 04_options_agent_*.md 05_decision_agent_*.md \
   .kiro/steering/

# Veri (ASCII adlarla)
cp "NEXUS_Agent_Veri_Seti_TEKNİK (1).xlsx"      data/nexus_agent_input.xlsx
cp "NEXUS_Hackathon_Veri_Seti_Ana veri.xlsx"    tests/fixtures/nexus_answer_key.xlsx

# Kaynak dokümanlar (steering dışı)
cp "Hackathon_Adımlar_Detay.docx"                                docs/kaynak/Hackathon_Adimlar_Detay.docx
cp "NEXUS – Hackathon Hazırlık Kiti_final.pdf"                   docs/kaynak/NEXUS_Hackathon_Hazirlik_Kiti.pdf
cp "Welcome Session - Agentic AI in Supply Chain Hackathon .pdf" docs/kaynak/Welcome_Session.pdf

printf ".env\n.venv/\n__pycache__/\n*.pyc\n" > .gitignore
git add . && git commit -m "NEXUS: steering + veri + kaynaklar"
```

**AWS ön koşulu:** Kiro'nun terminalinde `aws sts get-caller-identity` hackathon hesabını göstermeli. Kimlik bilgisini dosyaya yazma; profil veya ortam değişkeni kullan.

---

## 2. Kiro'da kontrol et (≈2 dk)

1. Klasörü Kiro'da aç.
2. **Steering** panelinde 18 dosyayı gör:
   - **Always (5):** SCOPE, hackathon-rules, hackathon_kural_seti, nexus-data, 00_README_indeks
   - **fileMatch (13):** ortak şema ve 00–05 agent md'leri
3. Kiro'nun hangi modelle çalıştığını kontrol et. Bu, agent'ların Bedrock modelinden bağımsızdır.

---

## 3. Adım A: anlama kontrolü (Vibe sohbeti)

Kod yazdırmadan önce Kiro'nun çerçeveyi doğru kurduğunu gör. Bu promptu **yeni bir sohbete** yapıştır:

```text
NEXUS projesine başlıyoruz. Henüz kod yazma ve dosya oluşturma.

1. .kiro/steering/SCOPE.md'yi ana çerçeve kabul et. Kaynak hiyerarşisi SCOPE §1'dedir.
   00_README_indeks.md yalnızca bilgi amaçlıdır ve değiştirilmeyecek.
2. Şunları oku: steering'deki kural md'leri, nexus-data.md, 00_ortak_veri_semalari.md ve
   00–05 agent md'lerinin tamamı (fileMatch olanları da şimdi açıkça oku). Gerektiğinde
   docs/kaynak/ altındaki docx ve Hazırlık Kiti'ne de bak.
3. Bana en fazla 25 madde halinde şunları ver:
   - Anladığın uçtan uca akış ve bulut mimarisi (SCOPE §4)
   - Her agent'ın tek cümlelik rolü, ürettiği sözleşme ve LLM'in o agent'taki sınırı
   - Geçerli proje kararlarından en kritik 8'i (SCOPE §5)
   - Kırmızı çizgiler (SCOPE §2)
   - Dokümanlar arasında hâlâ gördüğün çelişki, boşluk veya belirsizlik (varsa,
     hangi hiyerarşi kuralıyla çözülebileceğini de yaz; çözülemiyorsa soru olarak sor)
4. Sonra F0'da çalıştıracağın AWS kontrol komutlarını listele ama çalıştırma.
```

Kiro'nun cevabında yanlış bir şey varsa düzelt ve gerekiyorsa SCOPE §5'e karar ekletmesini iste. Sonra Adım B'ye geç.

---

## 4. Adım B: spec'i oluştur (Spec modu)

**Spec** modunda yeni bir spec başlat ve şu promptu ver:

```text
"nexus-mvp" adında bir spec oluştur. Çerçeve .kiro/steering/SCOPE.md'dir; §8.2'deki spec
kurallarına uy.

- requirements.md: SCOPE §6.1'deki fazların "bitti" kriterlerini ve §7.2'deki S1 kabul
  tablosunu EARS biçiminde gereksinimlere çevir. Her gereksinimin yanında kaynak md'yi ve
  bölümü yaz (ör. "03_impact_agent_kapsam_gorev.md §8"). What-if gereksinimi yazma (SCOPE D7).
- design.md: SCOPE §4 mimarisini, §3 bileşen haritasını ve §5 kararlarını esas al.
  Sözleşmeleri 00_ortak_veri_semalari.md'den al; D10 genişletmesini (KararKaydi v1.1) dahil et.
  SCOPE'ta olmayan bir tasarım kararı gerekiyorsa "KARAR GEREKLİ" diye işaretle ve bana sor.
- tasks.md: Görevleri F0–F7 olarak grupla; F8'i "opsiyonel" diye işaretle. Her görev için
  okunacak md'leri, değişecek klasörü ve görevin bitti testini yaz. SCOPE §6.2'deki paralel
  şeritleri görev başlıklarında göster.

Her belgeyi oluşturunca dur ve onayımı bekle.
```

Her belgeyi oku ve onayla. Atlamak istediğin bir şey varsa (ör. SES) burada söyle.

---

## 5. Adım C: fazları yürüt

`tasks.md`'de görevleri faz faz çalıştır. Her fazın başında kısa bir yönlendirme yeterli:

| Faz | Kiro'ya yazacağın |
|---|---|
| F0 | `tasks.md'deki F0 görevlerini yürüt. AWS'de kaynak oluşturan her komuttan önce onayımı al. Sonunda SCOPE §0.4 raporunu ver ve SES'in hazır olup olmadığını söyle.` |
| F1 | `F1'i yürüt. Önce 00_ortak_veri_semalari.md'yi v1.1'e güncelle (SCOPE D10, §5.1), sonra kodu yaz. Koruma testini (SCOPE §7.1) ekle.` |
| F2–F4 | `<Fx>'i yürüt. Bitti kriteri: SCOPE §6.1 ve §7.2'deki ilgili satırlar. Önce deterministik testleri, sonra -m llm testlerini çalıştır.` |
| F5 | `F5'i yürüt ve buluta deploy et. SG-2611-001 ile SINYAL_ISLE'yi buluttan çalıştır; S3'teki çıktıları ve Observability izlerini göster.` |
| F6 | `F6'yı yürüt. Önce yedek tetiği (S3'e yükleme) çalıştır, sonra SES'i bağla. UI için SCOPE §4.8'deki ekran tablosu esastır; what-if bağlantısı olmayacak.` |
| F7 | `F7'yi yürüt: demo_reset, toplu tarama (D17), kök README.md, docs/mimari/ çizimi. hackathon_kural_seti.md §7'deki kontrol listesini tek tek işaretle.` |

**Faz sonu kontrolü:** her faz bitince bu promptu ver.

```text
Bu fazın bitti kriterini SCOPE §6.1'e göre tek tek kontrol et. Çalıştırdığın testlerin
çıktısını özetle. KÇ1–KÇ12'den herhangi birini ihlal eden bir değişiklik var mı? Sıradaki
fazdan önce çözmemiz gereken bir şey kaldı mı?
```

---

## 6. Hook'ları kur (isteğe bağlı, ≈3 dk)

Kiro'nun hook panelinde doğal dille oluştur:

1. *"`src/contracts/` altında bir dosya kaydedilince `pytest tests/contracts -q` çalıştır ve sonucu özetle."*
2. *"`src/agents/<agent>/` altında bir dosya kaydedilince o agent'ın `tests/unit/<agent>` testlerini `-m 'not llm'` ile çalıştır."*
3. *Manuel hook "Kural denetimi":* "Değişikliklerde Bedrock dışı LLM SDK'sı (openai, anthropic, google.generativeai, ollama), `nexus_answer_key` referansı, sabit yazılmış parametre veya S1 cevap sabiti ve kişisel veri ara; bulguları listele."

---

## 7. Takımla paralel çalışma

F1 commit'lendikten sonra her kişi ayrı bir Kiro oturumunda kendi şeridini yürütür (SCOPE §6.2):

| Şerit | Klasör |
|---|---|
| A | `src/agents/impact` + `risk` |
| B | `src/agents/signal` |
| C | `src/agents/options` + `decision` |
| D | `infra/`, `src/triggers`, `src/api`, `ui/` |

Sözleşme değişikliği gerekirse yalnızca bir kişi yapar: önce ortak şema md'si, sonra `schemas.py` (G12).

**Zaman:** Final sunumlar 17:30'da. Zaman yetmezse SCOPE §6.3'teki kesme sırasını uygula.
