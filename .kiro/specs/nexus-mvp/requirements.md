# Requirements Document

## Introduction

NEXUS MVP, ilaç tedarik zincirinde kritik hammadde (API) sevkiyatlarını etkileyen olayları e-posta sinyallerinden otomatik tespit eden, etkiyi ve riski deterministik olarak hesaplayan, alternatif tedarik/lojistik stratejilerini üreten ve gerekçeli bir öneriyi insan onayına sunan çok ajanlı bir karar destek sistemidir. Sistem AWS üzerinde tek bir AgentCore Runtime (orkestratör + 5 Strands ajanı) olarak çalışır; S3'e düşen e-posta Lambda tetikleyicisini, o da Runtime'ı çağırır. Tüm sayısal hesaplar kodda (Python araçları) yapılır; LLM yalnızca sınır modellerinde (sinyal çıkarımı, dış koşul puanı, gerekçe metni) kullanılır ve kapatıldığında sistem şablon/kural yedeğiyle çalışır.

Bu doküman halihazırda uygulanmış ve dağıtılmış davranışı belgeler. Kaynak hiyerarşisi: `.kiro/steering/SCOPE.md` → ajan kapsam/kural md'leri → `00_ortak_veri_semalari.md` (şema v1.1).

## Glossary

- **NEXUS**: Tedarik zinciri risk tespit ve müdahale karar destek sistemi
- **Orkestratör**: `src/orchestrator/orchestrator.py`; ajanları sırayla çağıran, durum makinesini ve kalıcılığı yöneten bileşen
- **Signal_Agent / Risk_Agent / Impact_Agent / Options_Agent / Decision_Agent**: `src/agents/<ad>/agent.py` altındaki beş ajan
- **Email_Trigger**: `nexus-email-trigger` Lambda'sı (`src/triggers/email_trigger/handler.py`)
- **API**: `nexus-api` Lambda'sı, Function URL (`src/api/handler.py`)
- **Zarf**: Tüm ajan çıktılarının ortak üst modeli (run_id, uyarılar, kaynak referansları)
- **Sinyal**: `SG-2611-NNN` biçimli risk bildirimi
- **Risk Puanı**: Olasılık (1–5) × Etki (1–5); kademe Düşük / Orta / Yüksek
- **Strateji**: Bir veya birden çok bileşenden (transfer, alternatif tedarikçi, hava/deniz rotası) oluşan müdahale seçeneği
- **MCDA**: Maliyet, duruş, CO2 ve risk ağırlıklı çok kriterli puanlama
- **MILP**: Hibrit strateji miktar optimizasyonu (yalnızca S1)
- **Karar Kaydı**: İnsan onayı bekleyen/verilmiş karar dokümanı (`decisions/` öneki, `Karar_Kaydi` sayfası eşlemesi)
- **D0**: Analiz referans tarihi (25.11.2026)
- **S1**: Referans senaryo (SG-2611-001 / SV-26-1184 / MT100054)
- **NEXUS_LLM**: LLM'i açıp kapatan ortam değişkeni (`off` → deterministik yedek)

## Requirements

### Requirement 1: Ortak Veri Sözleşmeleri

**User Story:** As a geliştirici, I want tüm ajanların tek bir şema sürümüyle konuşmasını, so that ajanlar arası veri akışı doğrulanabilir ve kırılmaz olsun.

#### Acceptance Criteria

1. THE NEXUS SHALL tüm ajan girdi/çıktılarını `src/contracts/schemas.py` içindeki Pydantic v1.1 modelleriyle (SignalOutput, RiskOutput, ImpactOutput, OptionsOutput, DecisionOutput, KararKaydi) tanımlamak
2. THE NEXUS SHALL her ajan çıktısını ortak `Zarf` modelinden türetmek
3. WHEN bir model tanımsız alan aldığında, THE NEXUS SHALL doğrulama hatası üretmek
4. THE NEXUS SHALL LLM sınır modellerini (SignalLLMCikarimi, DisKosulBileseni, DecisionMetinLLM) ayrı modeller olarak işaretlemek

_Kaynak: 00_ortak_veri_semalari.md, SCOPE §3.1_

### Requirement 2: Veri Erişimi

**User Story:** As a ajan, I want sentetik Excel veri setine tek bir arayüzden erişmeyi, so that yerel ve bulut ortamında aynı kod çalışsın.

#### Acceptance Criteria

1. THE NEXUS SHALL veriyi `load_data(uri)` ile yerel dosyadan veya `s3://` URI'sinden okumak
2. THE NEXUS SHALL sayfa, satır ve parametre erişimini `NexusData.sheet / rows / param` ile sağlamak
3. WHILE aynı süreç ayaktayken, THE NEXUS SHALL veriyi `load_cached` ile bir kez yüklemek

_Kaynak: nexus-data.md, SCOPE §4.6_

### Requirement 3: E-postadan Sinyal Kaydı

**User Story:** As a tedarik zinciri analisti, I want gelen e-postaların otomatik olarak sinyale dönüşmesini, so that olaylar insan müdahalesi olmadan işlemeye girsin.

#### Acceptance Criteria

1. WHEN S3 `inbound-email/` önekine bir nesne yazıldığında, THE Email_Trigger SHALL MIME içeriğini ayrıştırmak
2. THE Email_Trigger SHALL gövdedeki e-posta adresi ve telefon numarası gibi kişisel verileri temizlemek
3. WHEN temizlenmiş metin girdi sinyallerinden biriyle eşleştiğinde, THE Email_Trigger SHALL mevcut `SG-2611-NNN` numarasını kullanmak
4. IF eşleşme yoksa, THEN THE Email_Trigger SHALL yeni bir sinyal numarası üreterek `signals/` önekine kaydetmek
5. WHEN sinyal kaydı hazır olduğunda, THE Email_Trigger SHALL AgentCore Runtime'ı `SINYAL_ISLE` eylemiyle çağırmak
6. THE NEXUS SHALL `inbound-email/` nesnelerini 1 gün sonra yaşam döngüsü kuralıyla silmek

_Kaynak: SCOPE §4.4, §4.5 (D6)_

### Requirement 4: Sinyal Çıkarımı ve Ayıklama

**User Story:** As a risk analisti, I want sinyal metninden sevkiyat, malzeme, gecikme ve ipuçlarının çıkarılmasını, so that ilgisiz sinyaller elensin ve ilgililer doğru sevkiyata bağlansın.

#### Acceptance Criteria

1. WHEN bir sinyal işlendiğinde, THE Signal_Agent SHALL ilgili sevkiyat, malzeme, olay tipi, tahmini gecikme ve alternatif ipuçlarını içeren SignalOutput üretmek
2. IF sinyal gürültü olarak sınıflanırsa, THEN THE Signal_Agent SHALL `isleme_karari = AYIKLA` ve ayıklama nedenini döndürmek
3. IF LLM kapalıysa veya yanıt vermezse, THEN THE Signal_Agent SHALL kural tabanlı eşleştirme ile çıkarım yapmak
4. WHEN SG-2611-001 işlendiğinde, THE Signal_Agent SHALL SV-26-1184, MT100054 ve 8 gün gecikme çıkarmak

_Kaynak: 01_signal_agent_veri_kurallari.md, SCOPE §7.2_

### Requirement 5: Etki Hesabı

**User Story:** As a üretim planlamacısı, I want stok kapsamı, duruş süresi ve maliyetlerin hesaplanmasını, so that aksiyonsuz kalmanın bedelini görebileyim.

#### Acceptance Criteria

1. THE Impact_Agent SHALL kullanılabilir tarihi ETA + gümrük + iç nakliye + kalite süreleriyle hesaplamak
2. THE Impact_Agent SHALL günlük tüketim, kapsama günü ve tükenme zamanını hesaplamak
3. THE Impact_Agent SHALL açık gün, duruş maliyeti, riskteki siparişler ve cezaları hesaplayarak aksiyonsuz maliyeti üretmek
4. THE Impact_Agent SHALL etki puanını (1–5) eşik tablosundan belirlemek
5. WHEN birden çok malzeme eşleştiğinde, THE Impact_Agent SHALL malzeme başına bir ImpactOutput döndürmek
6. WHEN S1 işlendiğinde, THE Impact_Agent SHALL 60,69 kg/gün, 9,89 gün kapsama, 5,11 gün duruş ve 2.741.018 TL aksiyonsuz maliyet üretmek

_Kaynak: 03_impact_agent_kapsam_gorev.md §8, SCOPE §7.2_

### Requirement 6: Risk Puanlama

**User Story:** As a risk yöneticisi, I want olasılık ve etkiden türetilmiş bir risk puanı ve kademesi, so that hangi olayın müdahale gerektirdiğini bileyim.

#### Acceptance Criteria

1. THE Risk_Agent SHALL olasılığı performans, finansal ve dış koşul bileşenlerinden hesaplamak
2. THE Risk_Agent SHALL dış koşul bileşenini LLM sınır modeli `DisKosulBileseni` ile almak ve LLM kapalıyken kural yedeğine düşmek
3. THE Risk_Agent SHALL risk puanını Olasılık × Etki olarak hesaplayıp Düşük/Orta/Yüksek kademesine atamak
4. IF kademe Yüksek değilse, THEN THE Orkestratör SHALL akışı `IZLEME` durumunda bitirmek
5. WHEN S1 işlendiğinde, THE Risk_Agent SHALL Yüksek kademe üretmek

_Kaynak: 02_risk_agent_kapsam_gorev.md, 02_risk_agent_veri_kurallari.md, SCOPE §7.2_

### Requirement 7: Seçenek Üretimi

**User Story:** As a tedarik planlamacısı, I want kısıtları kontrol edilmiş alternatif stratejiler, so that uygulanabilir müdahaleleri karşılaştırabileyim.

#### Acceptance Criteria

1. THE Options_Agent SHALL depo transferi, alternatif tedarikçi ve alternatif rota bileşenlerinden stratejiler üretmek
2. THE Options_Agent SHALL her bileşen için MOQ, ruhsat kaydı, hazır miktar ve rota kısıtlarını `KisitKontrolu` olarak kaydetmek
3. THE Options_Agent SHALL elenen kaynakları nedenleriyle `ElenenKaynak` listesinde döndürmek
4. WHEN S1 işlendiğinde, THE Options_Agent SHALL hibrit strateji dahil 6 strateji üretmek

_Kaynak: 04_options_agent_kapsam_gorev.md, 04_options_agent_veri_kurallari.md, SCOPE §7.2_

### Requirement 8: Karar ve Öneri

**User Story:** As a karar verici, I want stratejilerin simüle edilip sıralanmasını ve gerekçeli bir öneri kartını, so that bilinçli onay verebileyim.

#### Acceptance Criteria

1. THE Decision_Agent SHALL her strateji için günlük stok simülasyonu yaparak duruş gününü hesaplamak
2. THE Decision_Agent SHALL maliyet kalemlerini (aksiyon, duruş, ceza, stok taşıma) ve MCDA puanını hesaplayıp sıralamak
3. WHERE senaryo S1 ise, THE Decision_Agent SHALL hibrit miktarı MILP ile optimize etmek (PuLP, yoksa SciPy, yoksa sayım yedeği)
4. THE Decision_Agent SHALL gerekçe metnini LLM ile üretmek ve metindeki her sayının izinli sayılar listesinde olduğunu doğrulamak
5. IF sayı testi başarısız olursa veya LLM kapalıysa, THEN THE Decision_Agent SHALL şablon gerekçeyi kullanmak
6. WHEN S1 işlendiğinde, THE Decision_Agent SHALL S1-HIB stratejisini önermek

_Kaynak: 05_decision_agent_kapsam_gorev.md, 05_decision_agent_veri_kurallari.md, CALCULATIONS.md, SCOPE §7.2_

### Requirement 9: Orkestrasyon ve Durum Makinesi

**User Story:** As a operasyon sorumlusu, I want her çalıştırmanın izlenebilir bir durum geçmişi olmasını, so that akışın nerede bittiğini görebileyim.

#### Acceptance Criteria

1. WHEN `SINYAL_ISLE` eylemi (`sinyal_isle`) çağrıldığında, THE Orkestratör SHALL Signal → Impact → Risk → Options → Decision sırasını uygulamak
2. THE Orkestratör SHALL çalıştırmayı KAPAT, IZLEME, UYARI, ONAY_BEKLIYOR veya HATA durumlarından biriyle bitirmek
3. THE Orkestratör SHALL çalıştırma özetini ve ajan çıktılarını `runs/<run_id>/` altında saklamak
4. WHEN akış ONAY_BEKLIYOR ile bittiğinde, THE Orkestratör SHALL `decisions/` altına bir Karar Kaydı yazmak ve bildirim göndermek
5. IF bir ajan istisna fırlatırsa, THEN THE Orkestratör SHALL durumu HATA olarak kaydetmek
6. THE Orkestratör SHALL her ajan adımını OpenTelemetry span'i ile izlemek
7. THE Orkestratör SHALL `toplu_tarama` ile birden çok sinyali sırayla işlemek

_Kaynak: 00_orkestrator_kapsam_gorev.md, 00_orkestrator_veri_kurallari.md, SCOPE §4.1_

### Requirement 10: İnsan Onayı

**User Story:** As a karar verici, I want öneriyi onaylamak veya reddetmek, so that son söz insanda olsun.

#### Acceptance Criteria

1. WHEN `insan_karari` çağrıldığında, THE Orkestratör SHALL Karar Kaydı'nı onay/ret, karar veren ve zaman bilgisiyle güncellemek
2. THE NEXUS SHALL hiçbir stratejiyi insan onayı olmadan uygulanmış saymamak

_Kaynak: SCOPE §5.1, 05_decision_agent_kapsam_gorev.md_

### Requirement 11: API

**User Story:** As a UI, I want çalıştırma, karar ve harita verisine HTTP ile erişmeyi, so that kullanıcı sonuçları tarayıcıdan görebilsin.

#### Acceptance Criteria

1. THE API SHALL `GET /runs`, `GET /runs/{id}`, `GET /decisions`, `POST /decision`, `POST /email`, `GET /health` uçlarını sunmak
2. THE API SHALL `GET /map` dışındaki tüm uçlarda `x-api-key` başlığını doğrulamak
3. THE API SHALL `GET /map` ile tedarik zinciri harita verisini anahtarsız (sentetik veri) döndürmek
4. WHEN `POST /email` çağrıldığında, THE API SHALL içeriği `inbound-email/` önekine yazarak tetikleyiciyi başlatmak
5. THE API SHALL CORS ön kontrol (OPTIONS) isteklerini yanıtlamak

_Kaynak: SCOPE §4.2, §4.8 (D14)_

### Requirement 12: Kullanıcı Arayüzü ve Harita

**User Story:** As a analist, I want çalıştırmaları, öneri kartını ve tedarik zinciri haritasını görmek, so that durumu tek ekrandan takip edeyim.

#### Acceptance Criteria

1. THE NEXUS SHALL statik `ui/index.html` arayüzünü S3 statik web sitesi olarak yayınlamak
2. THE NEXUS SHALL `frontend/tedarik-zinciri.html` haritasını CloudFront üzerinden yayınlamak ve ajan verisini `GET /map` ucundan okumak
3. THE NEXUS SHALL harita verisini `scripts/build_map_data.py` ile `map/` önekine üretmek

_Kaynak: SCOPE §4.8 (D14)_

### Requirement 13: LLM Kullanımı ve Yedek

**User Story:** As a geliştirici, I want LLM'i tek bir yerden yönetmeyi, so that model değişikliği ve çevrimdışı test kolay olsun.

#### Acceptance Criteria

1. THE NEXUS SHALL tüm LLM çağrılarını `src/common/llm.py` (`structured`, `text`) üzerinden Strands + Bedrock ile yapmak
2. WHILE `NEXUS_LLM=off` iken, THE NEXUS SHALL hiçbir LLM çağrısı yapmadan deterministik yedeklerle çalışmak
3. THE NEXUS SHALL hiçbir sayısal sonucu LLM'e hesaplatmamak

_Kaynak: LLM_GUIDELINES.md, SCOPE §2, §4.3_

### Requirement 14: Dağıtım ve Demo

**User Story:** As a takım, I want tek komutla dağıtım ve demo sıfırlama, so that sunum öncesi ortam tekrarlanabilir olsun.

#### Acceptance Criteria

1. THE NEXUS SHALL `scripts/deploy_all.sh` ile S3, Lambda'lar, AgentCore Runtime ve UI'ı dağıtmak
2. THE NEXUS SHALL `scripts/demo_reset.py` ile `runs/`, `registry/`, `decisions/`, `signals/`, `inbound-email/` ve `exports/` öneklerini temizlemek
3. THE NEXUS SHALL `scripts/send_test_email.sh` ile uçtan uca test e-postası göndermeyi desteklemek
4. THE NEXUS SHALL bağımlılık sürümlerini `requirements.txt` içinde sabitlemek

_Kaynak: SCOPE §4.7 (D2), §6_
