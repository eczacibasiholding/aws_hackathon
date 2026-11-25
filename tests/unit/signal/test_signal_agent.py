import os
from pathlib import Path

import pandas as pd
import pytest

os.environ["NEXUS_LLM"] = "off"
from src.agents.signal import agent  # noqa: E402
from src.data_access.loader import load_data  # noqa: E402

KEY = Path(__file__).resolve().parents[2] / "fixtures" / "nexus_answer_key.xlsx"


@pytest.fixture(scope="module")
def data():
    return load_data()


@pytest.fixture(scope="module")
def beklenen():
    df = pd.read_excel(KEY, sheet_name="Risk_Sinyalleri", dtype=str)
    return {r["Sinyal No"]: r for r in df.to_dict("records")}


def test_list_signals(data):
    s = agent.list_signals(data)
    assert "SG-2611-001" in s and "SG-2611-002H" in s


def test_s1_signal_001(data, beklenen):
    o = agent.run(data, "SG-2611-001", "t")
    b = beklenen["SG-2611-001"]
    assert o.isleme_karari == "ANALIZ"
    assert o.ilgili_sevkiyat == [b["İlgili Sevkiyat (LLM)"]]
    assert o.ilgili_malzeme == b["İlgili Malzeme (LLM)"].split("; ")
    assert o.tahmini_gecikme_gun == pytest.approx(float(b["Tahmini Gecikme (gün) (LLM)"]), abs=0.01)
    assert "Mersin" in o.alternatif_ipucu and "Mersin" in b["Alternatif İpucu (LLM)"]
    assert "değişikliği" in o.alternatif_ipucu
    assert o.sinyal_guvenilirligi == int(b["Sinyal Güvenilirliği (1-5)"])
    assert b["İlgili Taraf (LLM)"] in o.ilgili_taraf
    assert o.kanit.metin_alintilari and all(a in data.rows("Risk_Sinyalleri")[0]["Ham Metin (LLM Girdisi)"]
                                            for a in o.kanit.metin_alintilari)


def test_s1_signal_002_same_shipment(data, beklenen):
    o1, o2 = agent.run(data, "SG-2611-001", "t"), agent.run(data, "SG-2611-002", "t")
    assert o2.isleme_karari == "ANALIZ"
    assert o2.ilgili_sevkiyat == o1.ilgili_sevkiyat == [beklenen["SG-2611-002"]["İlgili Sevkiyat (LLM)"]]
    g = agent.group_signals(data)
    assert g["SG-2611-001"] == g["SG-2611-002"]


@pytest.mark.parametrize("sn", ["SG-2611-005", "SG-2611-008", "SG-2611-003", "SG-2611-018"])
def test_generalization_shipment(data, beklenen, sn):
    o = agent.run(data, sn, "t")
    assert o.ilgili_sevkiyat == [beklenen[sn]["İlgili Sevkiyat (LLM)"]]


def test_noise(data):
    gurultu = [s for s in agent.list_signals(data)
               if s.startswith("SG-2610-") or s.endswith("H")
               or s in {f"SG-2611-0{i}" for i in range(13, 18)}]
    assert len(gurultu) >= 12
    for s in gurultu:
        o = agent.run(data, s, "t")
        assert o.isleme_karari == "AYIKLA", s
        assert o.ayiklama_nedeni


def test_reliability_all(data, beklenen):
    for s in agent.list_signals(data):
        assert agent.run(data, s, "t").sinyal_guvenilirligi == int(beklenen[s]["Sinyal Güvenilirliği (1-5)"]), s


def test_no_answer_key_in_src():
    src = Path(__file__).resolve().parents[3] / "src" / "agents" / "signal"
    for p in src.rglob("*.py"):
        t = p.read_text()
        assert "nexus_answer_key" not in t and "SV-26-1184" not in t and "Mersin" not in t
