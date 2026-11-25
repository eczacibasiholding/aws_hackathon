import pytest
from src.agents.decision import agent as decision_agent
from src.agents.decision.tools import milp as milp_t
from src.agents.decision.tools import rationale as rat
from src.agents.options import agent as options_agent


@pytest.fixture(scope="module")
def out(data, impact_s1, risk_s1):
    opt = options_agent.run(data, None, impact_s1, risk_s1, "t")
    return decision_agent.run(data, None, impact_s1, risk_s1, opt, "t")


def test_comparison_matches_answer_key(out, answer):
    exp = answer["Strateji_Karsilastirma"]
    exp = exp[exp["Senaryo"] == "S1"].set_index("Strateji Kodu")
    got = {k.strateji_kodu: k for k in out.karsilastirma}
    assert set(got) == set(exp.index)
    for kod, r in exp.iterrows():
        k = got[kod]
        assert abs(k.durus_gun - r["Duruş Günü (Simülasyon)"]) < 0.01, kod
        assert abs(k.toplam_maliyet_try - r["Toplam Maliyet (TRY)"]) < 1, kod
        assert abs(k.maliyet_kalemleri.ceza - r["Müşteri Ceza Maliyeti (TRY)"]) < 1, kod
        assert abs(k.maliyet_kalemleri.stok_tasima - r["Stok Taşıma Maliyeti (TRY)"]) < 1, kod
        assert abs(k.co2_kg - r["Ek CO2 (kg)"]) < 0.5, kod
        assert k.risk == r["Uygulama Riski (1-5)"], kod
        assert abs(k.agirlikli_skor - r["Ağırlıklı Skor (0-1)"]) < 0.001, kod
        assert k.sira == r["Sıra"], kod
        assert (k.oneri == "ÖNERİLEN") == (r["Öneri"] == "ÖNERİLEN"), kod


def test_recommendation_card(out, answer):
    exp = answer["Strateji_Karsilastirma"].set_index("Strateji Kodu").loc["S1-HIB"]
    kart = out.oneri_karti
    assert kart.onerilen_strateji_kodu == "S1-HIB"
    assert kart.rakamlar.durus_gun == 0
    assert abs(kart.rakamlar.toplam_maliyet_try - exp["Toplam Maliyet (TRY)"]) < 1
    assert abs(kart.rakamlar.tasarruf_try - exp["Aksiyonsuza Göre Tasarruf (TRY)"]) < 1
    assert kart.olay_tipi == "Birleşik (Tedarik + Lojistik)"
    assert kart.gerekce and "109.567" in kart.gerekce
    assert out.karar_kaydi_taslagi.karar == "Onay Bekliyor"
    assert any(u.kod == "LLM_HATA" for u in out.uyarilar)  # NEXUS_LLM=off → şablon


def test_milp(out, answer):
    exp = answer["Strateji_Karsilastirma"].set_index("Strateji Kodu").loc["S1-HIB"]
    m = out.milp
    assert m.durum == "OPTIMAL" and m.y_C == 0 and m.cckv_ile_uyumlu
    assert abs(m.x_T - 260) < 0.5 and abs(m.x_A - 250) < 0.5
    assert abs(m.amac_try + exp["Stok Taşıma Maliyeti (TRY)"] - exp["Toplam Maliyet (TRY)"]) < 1


def test_simulation_61_days(out):
    hib = next(s for s in out.simulasyon if s.strateji_kodu == "S1-HIB")
    assert len(hib.gunler) == 61 and hib.gunler[1].giris == 260 and hib.gunler[8].giris == 250


def test_milp_unavailable_warning(data, impact_s1, risk_s1, monkeypatch):
    monkeypatch.setattr(milp_t, "solve_milp", lambda p: None)
    opt = options_agent.run(data, None, impact_s1, risk_s1, "t")
    o = decision_agent.run(data, None, impact_s1, risk_s1, opt, "t")
    assert any(u.kod == "MILP_YAPILAMADI" for u in o.uyarilar)
    assert o.oneri_karti.onerilen_strateji_kodu == "S1-HIB"


def test_number_test():
    izinli = rat.allowed_numbers([109567.22, 2741018.17, 0, 260, 250])
    assert rat.number_test("Depodaki 260 kg ve uçakla 250 kg ile hat durmuyor; maliyet 110 bin TL.", izinli)
    assert rat.number_test("Maliyet 109.567 TL, kayıp 2,7 milyon TL.", izinli)
    assert not rat.number_test("Maliyet 95.000 TL.", izinli)


def test_llm_text_failing_number_test_falls_back(data, impact_s1, risk_s1, monkeypatch):
    from src.contracts.schemas import DecisionMetinLLM
    from src.common import llm
    monkeypatch.setattr(llm, "structured", lambda *a, **k: DecisionMetinLLM(gerekce="Maliyet 777.777 TL."))
    opt = options_agent.run(data, None, impact_s1, risk_s1, "t")
    o = decision_agent.run(data, None, impact_s1, risk_s1, opt, "t")
    assert "777" not in o.oneri_karti.gerekce
    assert any(u.kod == "LLM_HATA" and "rakam" in u.mesaj for u in o.uyarilar)
