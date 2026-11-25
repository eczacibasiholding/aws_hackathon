"""S1 uçtan uca (SCOPE §5.1, §7.2): SG-2611-001 → ONAY_BEKLIYOR, karar kaydı cevap anahtarındaki NXS-26-S1 ile uyumlu.
Beklenen değerler yalnızca cevap anahtarından okunur."""
from pathlib import Path

import pandas as pd
import pytest

ANAHTAR = Path(__file__).resolve().parents[1] / "fixtures" / "nexus_answer_key.xlsx"


@pytest.fixture()
def akis(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("NEXUS_LLM", "off")
    monkeypatch.delenv("NEXUS_BUCKET", raising=False)
    from src.orchestrator import orchestrator
    # Bedrock bu ortamda yok: Risk'in LLM bileşeni (dış koşul) testte cevap anahtarından verilir (SCOPE §7.1).
    from src.agents.risk import agent as risk
    from tests.unit.risk.test_risk_agent import ANSWER, _dk
    exp = pd.read_excel(ANSWER, sheet_name="Risk_Skorlama").set_index("Risk No")
    dk = lambda sig: _dk(exp, "R-01")  # S1 = cevap anahtarında R-01
    gercek = risk.run
    monkeypatch.setattr(risk, "run", lambda data, sig, imps, run_id, **kw: gercek(data, sig, imps, run_id, dis_kosul=dk(sig), **kw))
    return orchestrator


def _beklenen():
    df = pd.read_excel(ANAHTAR, sheet_name="Karar_Kaydi")
    return df[df["Olay No"] == "NXS-26-S1"].iloc[0]


def test_s1_onay_bekliyor(akis):
    from src.orchestrator.store import Store
    oz = akis.sinyal_isle({"sinyal_no": "SG-2611-001"})
    assert oz["durum"] == "ONAY_BEKLIYOR", oz
    assert oz["risk"]["kademe"] == "Yüksek"
    k = Store().get(f"decisions/{oz['olay_no']}.json")
    b = _beklenen()
    assert k["karar"] == "Onay Bekliyor"
    assert k["kurulus_kodu"] == b["Kuruluş Kodu"]
    assert abs(k["aksiyonsuz_maliyet_try"] - b["Aksiyonsuz Tahmini Maliyet (TRY)"]) <= 1
    assert abs(k["onerilen_maliyet_try"] - b["Aksiyon Maliyeti (TRY)"]) <= 1
    assert abs(k["tasarruf_try"] - b["Net Tasarruf (TRY)"]) <= 1
    assert abs(k["onlenen_durus_gun"] - b["Önlenen Duruş (gün)"]) <= 0.01
    assert k["risk_gerceklesmeden_aksiyon"] is True and k["yanlis_alarm_mi"] is False
    for a in ("signal", "risk", "impact", "options", "decision"):
        assert Store().get(f"runs/{oz['run_id']}/{a}.json") is not None


def test_onay(akis):
    oz = akis.sinyal_isle({"sinyal_no": "SG-2611-001"})
    r = akis.insan_karari({"olay_no": oz["olay_no"], "karar": "Onaylandı"})
    assert r["karar_kaydi"]["karar"] == "Onaylandı"


@pytest.mark.parametrize("sn", ["SG-2611-013", "SG-2611-017"])
def test_gurultu_kapat(akis, sn):
    assert akis.sinyal_isle({"sinyal_no": sn})["durum"] == "KAPAT"
