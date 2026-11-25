"""S1 fixture'ları: Impact/Risk çıktıları cevap anahtarından kurulur (yalnızca testlerde)."""
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.contracts.schemas import ImpactOutput, RiskAltindakiSiparis, RiskOutput, RiskBilesenleri, PerformansBileseni, DisKosulBileseni
from src.data_access.loader import load_data

ANSWER = Path(__file__).resolve().parents[2] / "fixtures" / "nexus_answer_key.xlsx"


@pytest.fixture(scope="session")
def data():
    return load_data()


@pytest.fixture(scope="session")
def answer():
    return {s: pd.read_excel(ANSWER, sheet_name=s) for s in
            ["Etki_Analizi", "Musteri_Siparisleri", "Risk_Skorlama", "Strateji_Bilesenleri", "Strateji_Karsilastirma"]}


@pytest.fixture(scope="session")
def impact_s1(data, answer):
    e = answer["Etki_Analizi"].set_index("Risk No").loc["R-01"]
    m = answer["Musteri_Siparisleri"]
    m = m[(m["Hat Kodu"] == e["Hat Kodu"]) & (m["Olası Ceza (TRY)"] > 0)]
    now = datetime.now(timezone.utc)
    return ImpactOutput(
        run_id="t", risk_no="R-01", senaryo="S1", d0=data.d0, baslangic_zamani=now, bitis_zamani=now, durum="TAMAM",
        sevkiyat_no=e["Etkilenen Sevkiyat"], malzeme_no=e["Malzeme No"], tesis_kodu=e["Tesis Kodu"], hat_kodu=e["Hat Kodu"],
        olcu_birimi="KG", serbest_stok=e["Serbest Stok"], gunluk_tuketim=e["Günlük Tüketim"],
        stok_kapsama_gun=e["Stok Kapsama (gün)"], tukenme_tarihi=e["Tükenme Tarihi"].to_pydatetime(),
        planlanan_kullanilabilir_tarih=e["Planlanan Kullanılabilir Tarih"].date(),
        guncel_kullanilabilir_tarih=e["Güncel Kullanılabilir Tarih"].date(), kullanilabilir_gun=e["Kullanılabilir Gün (D0+)"],
        acik_durus_gun=e["Açık / Duruş (gün)"], gunluk_durus_maliyeti_try=e["Günlük Duruş Maliyeti (TRY)"],
        yeniden_baslatma_maliyeti_try=e["Yeniden Başlatma Maliyeti (TRY)"], durus_maliyeti_try=e["Duruş Maliyeti (TRY)"],
        risk_altindaki_siparisler=[RiskAltindakiSiparis(siparis_no=r["Sipariş No"], hat_kodu=r["Hat Kodu"],
                                                        gecikme_gun=r["Tahmini Gecikme (gün)"], ceza_try=r["Olası Ceza (TRY)"])
                                   for r in m.to_dict("records")],
        olasi_ceza_try=e["Olası Müşteri Cezası (TRY)"], aksiyonsuz_maliyet_try=e["Aksiyonsuz Toplam Maliyet (TRY)"],
        etki_puani=int(e["Etki Puanı (1-5)"]), kaynak=[])


@pytest.fixture(scope="session")
def risk_s1(data, answer):
    r = answer["Risk_Skorlama"].set_index("Risk No").loc["R-01"]
    now = datetime.now(timezone.utc)
    return RiskOutput(
        run_id="t", risk_no="R-01", senaryo="S1", d0=data.d0, baslangic_zamani=now, bitis_zamani=now, durum="TAMAM",
        bilesenler=RiskBilesenleri(sinyal=int(r["Sinyal Güvenilirliği (1-5)"]),
                                   performans=PerformansBileseni(puan=int(r["Taraf Performans Puanı (1-5)"])),
                                   dis_kosul=DisKosulBileseni(puan=int(r["Dış Koşul Puanı (1-5)"])),
                                   finansal=int(r["Finansal Puan (1-5)"])),
        olasilik=r["Olasılık (1-5)"], etki=int(r["Etki (1-5)"]), risk_puani=r["Risk Puanı (1-25)"],
        risk_kademesi=r["Risk Kademesi"], kaynak=[])
