"""Impact Agent testleri — beklenen değerler yalnızca cevap anahtarından (Etki_Analizi, Musteri_Siparisleri)."""
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.agents.impact import agent as impact
from src.contracts.schemas import SignalKanit, SignalOutput
from src.data_access.loader import load_cached

ANSWER = Path(__file__).resolve().parents[2] / "fixtures" / "nexus_answer_key.xlsx"
SENARYO = {"R-01": ("S1", "SV-26-1184", "MT100054", "TS01"),
           "R-02": ("S2", "SV-26-1203", "MT100001", "TD5001"),
           "R-03": ("S3", "SV-26-1219", "MT100032", "TD5021")}


def signal_for(risk_no: str, **kw) -> SignalOutput:
    sen, sv, mt, taraf = SENARYO[risk_no]
    now = datetime(2026, 11, 25, 9)
    base = dict(run_id="t", d0="2026-11-25", baslangic_zamani=now, bitis_zamani=now, durum="TAMAM",
                senaryo=sen, risk_no=risk_no, sinyal_no="SG-2611-001", isleme_karari="ANALIZ",
                ilgili_taraf=[taraf], ilgili_sevkiyat=[sv], ilgili_malzeme=[mt], sinyal_guvenilirligi=5,
                bagli_risk_no=risk_no, kanit=SignalKanit(metin_alintilari=[]), kaynak=[])
    base.update(kw)
    return SignalOutput(**base)

import re as _re
from src.contracts import schemas as _sc
_ESKI = not _re.match(_sc.RiskAltindakiSiparis.model_fields["siparis_no"].metadata[0].pattern, "SO-26-7102")
_XF = pytest.mark.xfail(_ESKI, reason="contracts: SiparisNo deseni ^SO-26-5\\d{3}$ S2/S3 siparişlerini (SO-26-6/7/8xxx) reddediyor", strict=False)
S123 = ["R-01", pytest.param("R-02", marks=_XF), pytest.param("R-03", marks=_XF)]


@pytest.fixture(scope="module")
def data():
    return load_cached()


@pytest.fixture(scope="module")
def exp():
    return pd.read_excel(ANSWER, sheet_name="Etki_Analizi").set_index("Risk No")


@pytest.mark.parametrize("risk_no", S123)
def test_impact_matches_answer_key(data, exp, risk_no):
    out = impact.run(data, signal_for(risk_no), "t", what_if_gun=0)
    assert len(out) == 1
    o, e = out[0], exp.loc[risk_no]
    assert o.hat_kodu == e["Hat Kodu"] and o.tesis_kodu == e["Tesis Kodu"]
    assert o.serbest_stok == pytest.approx(e["Serbest Stok"])
    assert o.gunluk_tuketim == pytest.approx(e["Günlük Tüketim"], abs=0.01)
    assert o.stok_kapsama_gun == pytest.approx(e["Stok Kapsama (gün)"], abs=0.01)
    assert abs((o.tukenme_tarihi - pd.Timestamp(e["Tükenme Tarihi"]).to_pydatetime()).total_seconds()) < 60
    assert o.planlanan_kullanilabilir_tarih == pd.Timestamp(e["Planlanan Kullanılabilir Tarih"]).date()
    assert o.guncel_kullanilabilir_tarih == pd.Timestamp(e["Güncel Kullanılabilir Tarih"]).date()
    assert o.kullanilabilir_gun == pytest.approx(e["Kullanılabilir Gün (D0+)"], abs=0.01)
    assert o.acik_durus_gun == pytest.approx(e["Açık / Duruş (gün)"], abs=0.01)
    assert o.gunluk_durus_maliyeti_try == pytest.approx(e["Günlük Duruş Maliyeti (TRY)"], abs=1)
    assert o.durus_maliyeti_try == pytest.approx(e["Duruş Maliyeti (TRY)"], abs=1)
    assert len(o.risk_altindaki_siparisler) == e["Risk Altındaki Müşteri Siparişi"]
    assert o.olasi_ceza_try == pytest.approx(e["Olası Müşteri Cezası (TRY)"], abs=1)
    assert o.aksiyonsuz_maliyet_try == pytest.approx(e["Aksiyonsuz Toplam Maliyet (TRY)"], abs=1)
    assert o.etki_puani == e["Etki Puanı (1-5)"]
    assert o.risk_no == risk_no and o.senaryo == SENARYO[risk_no][0]


def test_s1_orders_match_answer_key(data):
    ms = pd.read_excel(ANSWER, sheet_name="Musteri_Siparisleri")
    ms = ms[(ms["Hat Kodu"] == "HAT-SG-03") & (ms["Etki Durumu"] == "Risk Altında")].set_index("Sipariş No")
    o = impact.run(data, signal_for("R-01"), "t", what_if_gun=0)[0]
    got = {s.siparis_no: s for s in o.risk_altindaki_siparisler}
    assert set(got) == set(ms.index)
    for no, s in got.items():
        assert s.gecikme_gun == pytest.approx(ms.loc[no, "Tahmini Gecikme (gün)"], abs=0.01)
        assert s.ceza_try == pytest.approx(ms.loc[no, "Olası Ceza (TRY)"], abs=1)


def test_what_if_adds_days_only_to_matching_scenario(data, exp):
    base = exp.loc["R-01", "Kullanılabilir Gün (D0+)"]
    o = impact.run(data, signal_for("R-01"), "t", what_if_gun=7)[0]
    assert o.kullanilabilir_gun == pytest.approx(base + 7)
    assert o.acik_durus_gun > exp.loc["R-01", "Açık / Duruş (gün)"]
    # parametre yolu: WhatIfGun=0 → değişiklik yok
    assert impact.run(data, signal_for("R-01"), "t")[0].kullanilabilir_gun == pytest.approx(base)


def test_unknown_shipment_returns_empty(data):
    assert impact.run(data, signal_for("R-01", ilgili_sevkiyat=["SV-26-9999"]), "t") == []
