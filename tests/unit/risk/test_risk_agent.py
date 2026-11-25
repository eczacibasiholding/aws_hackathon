"""Risk Agent testleri — beklenen değerler yalnızca cevap anahtarından (Risk_Skorlama)."""
from pathlib import Path

import pandas as pd
import pytest

from src.agents.impact import agent as impact
from src.agents.risk import agent as risk
from src.agents.risk.tools import scoring
from src.contracts.schemas import DisKosulBileseni
from src.data_access.loader import load_cached
from tests.unit.impact.test_impact_agent import S123, signal_for

ANSWER = Path(__file__).resolve().parents[2] / "fixtures" / "nexus_answer_key.xlsx"


@pytest.fixture(scope="module")
def data():
    return load_cached()


@pytest.fixture(scope="module")
def exp():
    return pd.read_excel(ANSWER, sheet_name="Risk_Skorlama").set_index("Risk No")


def _dk(exp, rn):
    return DisKosulBileseni(puan=int(exp.loc[rn, "Dış Koşul Puanı (1-5)"]),
                            gerekce=exp.loc[rn, "Dış Koşul Gerekçesi"], kanit_sinyaller=["SG-2611-001"])


@pytest.mark.parametrize("rn", S123)
def test_risk_with_given_external_score(data, exp, rn):
    sig = signal_for(rn, sinyal_guvenilirligi=int(exp.loc[rn, "Sinyal Güvenilirliği (1-5)"]))
    imps = impact.run(data, sig, "t", what_if_gun=0)
    out = risk.run(data, sig, imps, "t", dis_kosul=_dk(exp, rn))
    e = exp.loc[rn]
    assert out.bilesenler.performans.puan == e["Taraf Performans Puanı (1-5)"]
    assert out.bilesenler.finansal == e["Finansal Puan (1-5)"]
    assert out.olasilik == pytest.approx(e["Olasılık (1-5)"], abs=0.01)
    assert out.etki == e["Etki (1-5)"]
    assert out.risk_puani == pytest.approx(e["Risk Puanı (1-25)"], abs=0.01)
    assert out.risk_kademesi == e["Risk Kademesi"]
    assert out.agent_aksiyonu.split()[0] == e["Agent Aksiyonu"].split()[0].rstrip(":")


def test_offline_external_is_null_with_warning(data):
    sig = signal_for("R-01")
    out = risk.run(data, sig, impact.run(data, sig, "t", what_if_gun=0), "t")
    if out.bilesenler.dis_kosul.puan is None:
        assert out.olasilik is None and out.risk_puani is None and out.risk_kademesi is None
        assert any(u.kod in {"LLM_HATA", "KANIT_YETERSIZ"} for u in out.uyarilar)


def test_no_impact_no_score(data, exp):
    out = risk.run(data, signal_for("R-01"), [], "t", dis_kosul=_dk(exp, "R-01"))
    assert out.olasilik is not None and out.risk_puani is None and out.risk_kademesi is None


def test_tiers_from_params(data):
    assert scoring.classify_tier(data, 22)[0] == "Yüksek"
    assert scoring.classify_tier(data, 7)[0] == "Orta"
    assert scoring.classify_tier(data, 3.2)[0] == "Düşük"


def test_party_choice():
    assert scoring.choose_party(["TS01"], None)[0] == "TS01"
    assert scoring.choose_party(["TS01", "TD5011"], "Aktarma limanı gecikmesi")[0] == "TS01"
    assert scoring.choose_party(["TS01", "TD5011"], "Kalite OOS")[0] == "TD5011"


@pytest.mark.llm
def test_llm_external_score_s1(data, exp):
    from src.common.llm import llm_acik
    if not llm_acik():
        pytest.skip("Bedrock kapalı")
    sig = signal_for("R-01", olay_tipi="Aktarma limanı gecikmesi", ulke_bolge="Kızıldeniz / Cidde")
    out = risk.run(data, sig, impact.run(data, sig, "t", what_if_gun=0), "t")
    assert out.bilesenler.dis_kosul.puan == exp.loc["R-01", "Dış Koşul Puanı (1-5)"]
    assert out.risk_kademesi == exp.loc["R-01", "Risk Kademesi"]
