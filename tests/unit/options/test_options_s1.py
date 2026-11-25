import pytest
from src.agents.options import agent as options_agent


@pytest.fixture(scope="module")
def out(data, impact_s1, risk_s1):
    return options_agent.run(data, None, impact_s1, risk_s1, "t")


def _s(out, kod):
    return next(s for s in out.stratejiler if s.strateji_kodu == kod)


def test_six_strategies(out, answer):
    exp = answer["Strateji_Karsilastirma"]
    exp = set(exp[exp["Senaryo"] == "S1"]["Strateji Kodu"])
    assert len(out.stratejiler) == 6
    assert {s.strateji_kodu for s in out.stratejiler} == exp
    assert all(s.uygun_mu for s in out.stratejiler)


def test_transfer_260(out):
    b = _s(out, "S1-TRF").bilesenler[0]
    assert b.kaynak == "D-SG-01|MT100054" and b.miktar == 260


def test_components_match_answer_key(out, answer):
    exp = answer["Strateji_Bilesenleri"]
    exp = exp[(exp["Senaryo"] == "S1") & (exp["Bileşen Tipi"] != "Ana Sevkiyat") | (exp["Strateji Kodu"] == "S1-COD")]
    for kod, g in exp.groupby("Strateji Kodu"):
        bil = _s(out, kod).bilesenler
        assert len(bil) == len(g), kod
        for b, r in zip(bil, g.to_dict("records")):
            assert abs(b.miktar - r["Toplam Miktar"]) < 0.5
            assert abs(b.hazir_gun - r["Başlangıç Günü (D0+)"]) < 0.01
            assert abs(b.lojistik_maliyet_try - r["Lojistik Maliyeti (TRY)"]) < 1
            assert abs(b.ek_malzeme_maliyeti_try - r["Ek Malzeme Maliyeti (TRY)"]) < 1
            assert abs(b.test_maliyeti_try - r["Diğer Sabit Maliyet (TRY)"]) < 1
            assert abs(b.co2_kg - r["Ek CO2 (kg)"]) < 0.5
            assert b.uygulama_riski == r["Uygulama Riski (1-5)"]
            assert b.rota_kodu == r["Rota Kodu"]


def test_alt_supplier_and_route(out, data):
    hib = _s(out, "S1-HIB").bilesenler[1]
    assert hib.kaynak == "MT100054|TD5012" and hib.miktar == 250 and hib.hazir_gun == 8
    k = next(r for r in data.rows("Tedarik_Kaynaklari") if r["Kaynak Anahtarı"] == "MT100054|TD5012")
    assert k["Hazır Stok (birim)"] == 1500 and k["Spot MOQ (birim)"] == 250 and "Ruhsatta Kayıtlı" in k["Kalifikasyon Durumu"]
    r = next(r for r in data.rows("Rota_Secenekleri") if r["Rota Kodu"] == hib.rota_kodu)
    assert r["Kapı-Kapı Süre (gün)"] == 2 and r["Değişken Maliyet (USD/kg)"] == 4.6


def test_cod_passes(out):
    s = _s(out, "S1-COD")
    assert s.uygun_mu and s.bilesenler[0].tip == "ROTA_DEGISIKLIGI" and s.bilesenler[0].hazir_gun == 14


def test_s3_german_supplier_eliminated(data, impact_s1):
    from src.agents.options.sourcing.tools import check_qualification
    k = next(r for r in data.rows("Tedarik_Kaynaklari") if r["Kaynak Anahtarı"] == "MT100032|TD5023")
    assert check_qualification(data, k)["gecti"] is False
