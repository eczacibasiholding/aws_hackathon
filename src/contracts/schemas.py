"""Ortak sözleşmeler — 00_ortak_veri_semalari.md §5–§6 birebir."""
# src/contracts/schemas.py
from __future__ import annotations
from datetime import date, datetime
from typing import Annotated, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SEMA_VERSIYONU = "1.1"   # D10: KararKaydi genişletmesi (SCOPE §5.1)

# ---------- Kimlik tipleri (§3) ----------
def _id(p: str):
    return Annotated[str, StringConstraints(pattern=p)]

KurulusKodu   = _id(r"^(KARO|BANYO|MADEN|SAGLIK)$")
TesisKodu     = _id(r"^[TD]-(KR|BN|MD|SG)-0\d$")
MalzemeNo     = _id(r"^MT1000\d{2}$")
HatKodu       = _id(r"^HAT-(KR|BN|SG|MD)-0\d$")
TedarikciNo   = _id(r"^TD5\d{3}$")
TarafNo       = _id(r"^(TD5\d{3}|TS0[1-9])$")
SinyalNo      = _id(r"^SG-26(10|11)-0\d{2}H?$")
SevkiyatNo    = _id(r"^SV-26-\d{4}$")
RotaKodu      = _id(r"^R-(SEA|AIR|TRK|COD|CST|EXP|RAIL)-.+$")
SiparisNo    = _id(r"^SO-26-\d{4}$")
RiskNo        = _id(r"^R-\d{2}$")
StratejiKodu  = _id(r"^S[1-3]-[A-Z0-9-]+$")
KararNo       = _id(r"^NXS-26-0\d{2}$")
StokAnahtari  = _id(r"^[TD]-(KR|BN|MD|SG)-0\d\|MT1000\d{2}$")

Puan15 = Annotated[int, Field(ge=1, le=5)]

# ---------- Enum'lar (§4) ----------
Agent        = Literal["orkestrator", "signal", "risk", "impact", "options", "decision"]
Durum        = Literal["TAMAM", "UYARI", "HATA"]
Senaryo      = Literal["S1", "S2", "S3"]
Kademe       = Literal["Yüksek", "Orta", "Düşük"]
BilesenTipi  = Literal["TRANSFER", "ALTERNATIF_TEDARIK_ROTA", "ROTA_DEGISIKLIGI"]
KisitKodu    = Literal["C1", "C2", "C3", "C4", "C5", "C6"]
KisitSonuc   = Literal["GEÇTİ", "KALDI"]
KararDurumu  = Literal["Onaylandı", "Reddedildi", "Revize Edildi", "Onay Bekliyor"]
UyariKodu    = Literal["ESLESME_YOK", "COKLU_ADAY", "CELISKI", "EKSIK_BILESEN", "KANIT_YETERSIZ",
                       "BIRIM_UYUMSUZ", "HAZIR_DEGER_FARKI", "KISIT_KALDI", "UYGUN_STRATEJI_YOK",
                       "NORMALIZE_TANIMSIZ", "MILP_YAPILAMADI", "LLM_HATA", "SEMA_HATASI"]


class Sozlesme(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- Ortak parçalar ----------
class Uyari(Sozlesme):
    kod: UyariKodu
    mesaj: str
    alan: Optional[str] = None            # ilgili çıktı alanı


class KaynakRef(Sozlesme):
    sayfa: str                            # GİRDİ dosyasındaki sayfa adı, birebir
    anahtarlar: list[str]                 # PK değerleri (ör. "T-SG-01|MT100054")
    sutunlar: list[str] = []              # okunan sütun adları, birebir (opsiyonel)


class Zarf(Sozlesme):
    sema_versiyonu: str = SEMA_VERSIYONU
    run_id: str
    agent: Agent
    senaryo: Optional[Senaryo] = None     # girdide "-" ise None (izleme/gürültü)
    risk_no: Optional[RiskNo] = None
    d0: date                              # Parametreler → AnalizTarihi
    what_if_gun: float = 0                # Parametreler → WhatIfGun (uygulandığı hâli)
    baslangic_zamani: datetime
    bitis_zamani: datetime
    durum: Durum
    uyarilar: list[Uyari] = []

    @model_validator(mode="after")
    def _zaman(self):
        if self.bitis_zamani < self.baslangic_zamani:
            raise ValueError("bitis_zamani < baslangic_zamani")
        return self


# ---------- 01 · Signal ----------
class SignalKanit(Sozlesme):
    metin_alintilari: list[str]           # Ham Metin'den BİREBİR alıntılar
    eslesme_yolu: Optional[str] = None    # ör. "Takip No … → Sevkiyatlar.Takip No (Sahte) → SV-26-1184"


class SignalOutput(Zarf):
    agent: Literal["signal"] = "signal"
    sinyal_no: SinyalNo
    isleme_karari: Literal["ANALIZ", "AYIKLA"]
    ayiklama_nedeni: Optional[str] = None
    olay_tipi: Optional[str] = None                      # LLM
    ulke_bolge: Optional[str] = None                     # LLM
    ilgili_taraf: list[TarafNo] = []                     # LLM ipucu → tool doğrulama
    ilgili_sevkiyat: list[SevkiyatNo] = []               # tool (eşleştirme)
    ilgili_malzeme: list[MalzemeNo] = []                 # tool (eşleştirme)
    tahmini_gecikme_gun: Optional[float] = None          # LLM; metinde yoksa None
    alternatif_ipucu: Optional[str] = None               # LLM; değerlendirilmez
    sinyal_guvenilirligi: Puan15                         # tool
    tespit_gecikmesi_saat: Optional[float] = None        # tool
    bagli_risk_no: Optional[RiskNo] = None               # zarf risk_no ile aynı olmalı
    kanit: SignalKanit
    kaynak: list[KaynakRef]
    dogrulama_uyarilari: list[Uyari] = []

    @model_validator(mode="after")
    def _kurallar(self):
        if self.isleme_karari == "AYIKLA" and not self.ayiklama_nedeni:
            raise ValueError("AYIKLA için ayiklama_nedeni zorunlu")
        if self.bagli_risk_no and self.risk_no and self.bagli_risk_no != self.risk_no:
            raise ValueError("bagli_risk_no ≠ zarf risk_no")
        return self


# ---------- 02 · Risk ----------
class PerformansBileseni(Sozlesme):
    puan: Optional[Puan15] = None                        # tool (Esik_Tablolari)
    taraf: Optional[TarafNo] = None                      # TSxx → Tasiyicilar, TD5xxx → Tedarikciler
    kaynak_sutun: Optional[str] = None                   # "Zamanında Varış Oranı" | "OTIF Oranı"
    secim_gerekcesi: Optional[str] = None                # LLM


class DisKosulBileseni(Sozlesme):                        # LLM SINIR MODELİ (G10 istisnası)
    puan: Optional[Puan15] = None                        # kanıt yetersizse None
    gerekce: Optional[str] = None
    kanit_sinyaller: list[SinyalNo] = []


class RiskBilesenleri(Sozlesme):
    sinyal: Puan15
    performans: PerformansBileseni
    dis_kosul: DisKosulBileseni
    finansal: Optional[Puan15] = None


class RiskOutput(Zarf):
    agent: Literal["risk"] = "risk"
    bilesenler: RiskBilesenleri
    olasilik: Optional[float] = Field(None, ge=1, le=5)  # tool; eksik bileşende None
    etki: Optional[Puan15] = None                        # = ImpactOutput.etki_puani
    risk_puani: Optional[float] = Field(None, ge=1, le=25)
    risk_kademesi: Optional[Kademe] = None
    agent_aksiyonu: Optional[str] = None                 # tam analiz + onaya sun | uyarı + seçenek hazırda | izle
    aciklama: Optional[str] = None                       # LLM, kısa Türkçe
    kaynak: list[KaynakRef]

    @model_validator(mode="after")
    def _kurallar(self):
        if self.etki is None or self.olasilik is None:     # R-K4: etki yoksa puan/kademe yok
            if self.risk_puani is not None or self.risk_kademesi is not None:
                raise ValueError("etki/olasılık yokken risk_puani/kademe üretilemez")
        elif self.risk_puani is not None and abs(self.risk_puani - self.olasilik * self.etki) > 0.01:
            raise ValueError("risk_puani ≠ olasilik × etki")
        return self


# ---------- 03 · Impact ----------
class RiskAltindakiSiparis(Sozlesme):
    siparis_no: SiparisNo
    hat_kodu: Optional[HatKodu] = None
    gerekli_uretim_tarihi: Optional[date] = None
    gecikme_gun: float = Field(ge=0)
    gunluk_ceza_try: Optional[float] = Field(None, ge=0)
    ceza_try: float = Field(ge=0)


class ImpactOutput(Zarf):                                # malzeme başına bir çıktı (çoklu eşleşmede birden çok)
    agent: Literal["impact"] = "impact"
    sevkiyat_no: SevkiyatNo
    malzeme_no: MalzemeNo
    tesis_kodu: TesisKodu
    hat_kodu: HatKodu
    olcu_birimi: Optional[Literal["KG", "TON", "ADET"]] = None
    serbest_stok: float = Field(ge=0)                    # yalnızca Serbest Stok
    gunluk_tuketim: float = Field(gt=0)
    stok_kapsama_gun: float = Field(ge=0)
    tukenme_tarihi: datetime                             # kesirli gün → saat dahil
    planlanan_kullanilabilir_tarih: date
    guncel_kullanilabilir_tarih: date                    # varış + gümrük + iç nakliye + kalite (+ WhatIfGun)
    kullanilabilir_gun: float                            # gün indeksi (G5)
    acik_durus_gun: float = Field(ge=0)
    gunluk_durus_maliyeti_try: float = Field(ge=0)
    yeniden_baslatma_maliyeti_try: float = Field(ge=0)
    durus_maliyeti_try: float = Field(ge=0)
    risk_altindaki_siparisler: list[RiskAltindakiSiparis] = []
    olasi_ceza_try: float = Field(ge=0)
    aksiyonsuz_maliyet_try: float = Field(ge=0)
    etki_puani: Puan15
    kaynak: list[KaynakRef]

    @model_validator(mode="after")
    def _kurallar(self):
        if abs(self.aksiyonsuz_maliyet_try - (self.durus_maliyeti_try + self.olasi_ceza_try)) > 1:
            raise ValueError("aksiyonsuz ≠ duruş + ceza")
        if abs(self.olasi_ceza_try - sum(s.ceza_try for s in self.risk_altindaki_siparisler)) > 1:
            raise ValueError("olasi_ceza_try ≠ sipariş cezaları toplamı")
        return self


# ---------- 04 · Options ----------
class KisitKontrolu(Sozlesme):
    sonuc: KisitSonuc
    kontroller: list[KisitKodu]                          # uygulanan kısıtlar
    kalan_kisitlar: list[KisitKodu] = []                 # KALDI ise hangileri


class StratejiBileseni(Sozlesme):
    bilesen_no: int = Field(ge=1)
    tip: BilesenTipi
    kaynak: str                  # TRANSFER → Stok Anahtarı · ALTERNATIF_TEDARIK_ROTA → Kaynak Anahtarı · ROTA_DEGISIKLIGI → Sevkiyat No
    rota_kodu: Optional[RotaKodu] = None
    miktar: float = Field(gt=0)
    olcu_birimi: Optional[Literal["KG", "TON", "ADET"]] = None
    brut_kg: Optional[float] = Field(None, ge=0)
    hazir_gun: float = Field(ge=0)                       # gün indeksi (G5)
    lojistik_maliyet_try: float = Field(0, ge=0)
    ek_malzeme_maliyeti_try: float = 0                   # fiyat farkı; negatif olabilir
    test_maliyeti_try: float = Field(0, ge=0)
    co2_kg: float = Field(0, ge=0)
    uygulama_riski: Optional[Puan15] = None
    kisit_kontrolu: KisitKontrolu


class Strateji(Sozlesme):
    strateji_kodu: StratejiKodu
    strateji_adi: str
    bilesenler: list[StratejiBileseni] = []              # "Bekle" → []
    uygun_mu: bool
    eleme_nedeni: Optional[str] = None

    @model_validator(mode="after")
    def _kurallar(self):
        if not self.uygun_mu and not self.eleme_nedeni:
            raise ValueError("uygun olmayan strateji için eleme_nedeni zorunlu")
        return self


class ElenenKaynak(Sozlesme):
    kaynak: str                                          # Kaynak Anahtarı / Stok Anahtarı / Rota Kodu
    neden: str
    hazir_gun: Optional[float] = None                    # ör. kalifikasyon nedeniyle 56. gün


class OptionsOutput(Zarf):
    agent: Literal["options"] = "options"
    stratejiler: list[Strateji] = Field(min_length=1)
    elenen_kaynaklar: list[ElenenKaynak] = []
    kaynak: list[KaynakRef]

    @model_validator(mode="after")
    def _kurallar(self):
        if not any(len(s.bilesenler) == 0 for s in self.stratejiler):   # OP-K3
            raise ValueError("'Bekle / hiçbir şey yapma' stratejisi eksik")
        return self


# ---------- 05 · Decision ----------
class SimulasyonGunu(Sozlesme):
    gun: int = Field(ge=0, le=60)
    giris: float = Field(ge=0)                           # gün başı giriş
    gun_sonu_stok: float = Field(ge=0)
    durus_orani: float = Field(ge=0, le=1)               # kısmi duruş kesirli


class StratejiSimulasyonu(Sozlesme):
    strateji_kodu: StratejiKodu
    gunler: list[SimulasyonGunu] = Field(min_length=61, max_length=61)   # D0…D60


class MaliyetKalemleri(Sozlesme):
    durus: float = Field(ge=0)
    ceza: float = Field(ge=0)
    lojistik: float = Field(ge=0)
    ek_malzeme: float = 0
    test: float = Field(ge=0)
    stok_tasima: float = Field(ge=0)


class NormalizePuanlar(Sozlesme):                       # senaryo içi 0–1; bölen 0 ise None
    maliyet: Optional[float] = Field(None, ge=0, le=1)
    durus: Optional[float] = Field(None, ge=0, le=1)
    co2: Optional[float] = Field(None, ge=0, le=1)
    risk: Optional[float] = Field(None, ge=0, le=1)


class StratejiKarsilastirma(Sozlesme):
    strateji_kodu: StratejiKodu
    strateji_adi: Optional[str] = None
    uygun_mu: bool
    durus_gun: float = Field(ge=0)
    maliyet_kalemleri: MaliyetKalemleri
    toplam_maliyet_try: float = Field(ge=0)
    co2_kg: float = Field(ge=0)
    risk: Optional[float] = None
    normalize: NormalizePuanlar
    agirlikli_skor: Optional[float] = None
    sira: Optional[int] = Field(None, ge=1)              # uygun değilse None
    oneri: Optional[Literal["ÖNERİLEN"]] = None

    @model_validator(mode="after")
    def _kurallar(self):
        k = self.maliyet_kalemleri
        if abs(self.toplam_maliyet_try - (k.durus + k.ceza + k.lojistik + k.ek_malzeme + k.test + k.stok_tasima)) > 1:
            raise ValueError("toplam_maliyet_try ≠ kalemler toplamı")
        return self


class MilpSonucu(Sozlesme):                              # yalnızca S1
    durum: Literal["OPTIMAL", "COZUMSUZ", "ZAMAN_ASIMI"]
    x_T: Optional[float] = Field(None, ge=0)             # transfer (kg)
    x_A: Optional[float] = Field(None, ge=0)             # hava (kg)
    y_C: Optional[Literal[0, 1]] = None                  # COD (liman değişikliği)
    amac_try: Optional[float] = None
    cckv_ile_uyumlu: Optional[bool] = None


class OneriRakamlari(Sozlesme):
    durus_gun: float = Field(ge=0)
    toplam_maliyet_try: float = Field(ge=0)
    aksiyonsuz_maliyet_try: float = Field(ge=0)
    tasarruf_try: float


class DecisionMetinLLM(Sozlesme):                        # LLM SINIR MODELİ
    gerekce: str                                         # kısa, rakamlı, Türkçe; rakamlar yalnızca OneriRakamlari'ndan
    dikkat_notu: Optional[str] = None                    # MILP–ÇKKV çelişkisi vb.
    olay_tipi: Optional[Literal["Tedarik", "Lojistik", "Birleşik (Tedarik + Lojistik)"]] = None  # v1.1
    olay_ozeti: Optional[str] = None                     # v1.1, tek cümle; rakam testi geçerli


class OneriKarti(Sozlesme):
    baslik: str                                          # ekran metni (iş birimi onaylı)
    gerekce: Optional[str] = None                        # DecisionMetinLLM.gerekce; LLM hatasında None
    dikkat_notu: Optional[str] = None
    olay_tipi: Optional[Literal["Tedarik", "Lojistik", "Birleşik (Tedarik + Lojistik)"]] = None  # v1.1
    olay_ozeti: Optional[str] = None                     # v1.1
    onerilen_strateji_kodu: Optional[StratejiKodu] = None   # uygun strateji yoksa None
    rakamlar: OneriRakamlari
    butonlar: list[Literal["Onayla", "Reddet", "Değiştir"]] = ["Onayla", "Reddet", "Değiştir"]


class KararKaydiTaslagi(Sozlesme):
    olay_no: KararNo
    karar: Literal["Onay Bekliyor"] = "Onay Bekliyor"    # DC-K1
    tasarruf_try: Optional[float] = None
    oneri_zamani: datetime


class WhatIfKarsilastirma(Sozlesme):
    onceki_strateji_kodu: StratejiKodu
    onceki_stratejinin_yeni_durus_gun: float = Field(ge=0)   # S1 +7: ≈ 3,7
    yeni_strateji_kodu: Optional[StratejiKodu] = None
    oneri_degisti_mi: bool


class DecisionOutput(Zarf):
    agent: Literal["decision"] = "decision"
    simulasyon: list[StratejiSimulasyonu]
    karsilastirma: list[StratejiKarsilastirma] = Field(min_length=1)
    milp: Optional[MilpSonucu] = None
    oneri_karti: OneriKarti
    karar_kaydi_taslagi: KararKaydiTaslagi
    what_if_karsilastirma: Optional[WhatIfKarsilastirma] = None

    @model_validator(mode="after")
    def _kurallar(self):
        onerilen = [s for s in self.karsilastirma if s.oneri == "ÖNERİLEN"]
        if len(onerilen) > 1:
            raise ValueError("birden çok ÖNERİLEN")
        if onerilen:
            o = onerilen[0]
            if not o.uygun_mu or o.sira != 1:                                    # DC-K4
                raise ValueError("ÖNERİLEN, kısıtı geçen 1. sıra olmalı")
            if self.oneri_karti.onerilen_strateji_kodu != o.strateji_kodu:
                raise ValueError("kart stratejisi ≠ ÖNERİLEN")
        return self


# ---------- 00 · Orkestratör girdileri ve karar kaydı ----------
class WhatIfIstegi(Sozlesme):
    senaryo: Senaryo                                     # Parametreler → WhatIfSenaryo
    what_if_gun: float                                   # Parametreler → WhatIfGun (demo: 7)
    tetik: Literal["PARAMETRE", "YENI_SINYAL"]
    sinyal_no: Optional[SinyalNo] = None                 # YENI_SINYAL ise


class InsanKarari(Sozlesme):
    olay_no: KararNo
    karar: Literal["Onaylandı", "Reddedildi", "Revize Edildi"]
    onaylayan_rol: str                                   # rol; kişi adı DEĞİL (G11)
    karar_zamani: datetime
    revize_notu: Optional[str] = None                    # "Değiştir" seçildiyse
    yanlis_alarm: bool = False                           # v1.1 (SCOPE §5.1)


class KararKaydi(Sozlesme):
    olay_no: KararNo
    risk_no: RiskNo
    senaryo: Optional[Senaryo] = None
    sinyal_nolari: list[SinyalNo]
    sinyal_tespit_zamani: datetime
    oneri_zamani: datetime
    karar_zamani: Optional[datetime] = None
    karar: KararDurumu
    onaylayan_rol: Optional[str] = None
    onerilen_strateji_kodu: Optional[StratejiKodu] = None
    aksiyonsuz_maliyet_try: float = Field(ge=0)
    onerilen_maliyet_try: Optional[float] = Field(None, ge=0)
    tasarruf_try: Optional[float] = None
    tespit_suresi_dk: Optional[float] = Field(None, ge=0)
    oneri_suresi_dk: Optional[float] = Field(None, ge=0)
    onay_suresi_dk: Optional[float] = Field(None, ge=0)
    revize_notu: Optional[str] = None
    # ---- v1.1 (SCOPE D10, §5.1) ----
    tarih: Optional[date] = None
    kurulus_kodu: Optional[str] = None
    olay_tipi: Optional[Literal["Tedarik", "Lojistik", "Birleşik (Tedarik + Lojistik)"]] = None
    olay_ozeti: Optional[str] = None
    sinyal_yayin_zamani: Optional[datetime] = None
    onerilen_aksiyon: Optional[str] = None
    yanlis_alarm_mi: bool = False
    risk_gerceklesmeden_aksiyon: Optional[bool] = None
    onlenen_durus_gun: Optional[float] = None
    kullanici_geri_bildirimi: Optional[str] = None


class SignalLLMCikarimi(Sozlesme):                       # LLM SINIR MODELİ
    olay_tipi: Optional[str] = None
    ulke_bolge: Optional[str] = None
    taraf_adlari: list[str] = []                         # serbest metin adlar → tool: Tedarikciler / Tasiyicilar
    takip_no_ipuclari: list[str] = []                    # → tool: Sevkiyatlar.Takip No (Sahte)
    po_ipuclari: list[str] = []                          # → tool: Acik_Siparisler.PO No (str)
    gemi_adlari: list[str] = []                          # → tool: Sevkiyatlar.Son Konum / Not
    tahmini_gecikme_gun: Optional[float] = None          # metinde açık değilse None
    alternatif_ipucu: Optional[str] = None
    alintilar: dict[str, str] = {}                       # alan adı → Ham Metin'den birebir alıntı
