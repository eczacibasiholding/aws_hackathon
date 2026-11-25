"""H3–H5, H7: maliyet kalemleri, ÇKKV normalize + ağırlıklı skor, sıralama."""
from __future__ import annotations

from src.contracts.schemas import MaliyetKalemleri, NormalizePuanlar, Strateji


def holding_cost(miktar: float, birim_try: float, oran: float, gunluk: float) -> float:
    """Formuller #33."""
    if gunluk <= 0:
        return 0.0
    return miktar * birim_try * oran * 0.5 * (miktar / gunluk) / 365


def compute_total_cost(strateji: Strateji, durus_gun: float, impact, birim_try: float, oran: float) -> MaliyetKalemleri:
    durus = durus_gun * impact.gunluk_durus_maliyeti_try + (impact.yeniden_baslatma_maliyeti_try if durus_gun > 1e-9 else 0.0)
    ceza = 0.0 if impact.acik_durus_gun <= 0 else impact.olasi_ceza_try * min(1.0, durus_gun / impact.acik_durus_gun)
    b = strateji.bilesenler
    return MaliyetKalemleri(
        durus=durus, ceza=ceza, lojistik=sum(x.lojistik_maliyet_try for x in b),
        ek_malzeme=sum(x.ek_malzeme_maliyeti_try for x in b), test=sum(x.test_maliyeti_try for x in b),
        stok_tasima=sum(holding_cost(x.miktar, birim_try, oran, impact.gunluk_tuketim)
                        for x in b if x.tip == "ALTERNATIF_TEDARIK_ROTA"))


def total(k: MaliyetKalemleri) -> float:
    return k.durus + k.ceza + k.lojistik + k.ek_malzeme + k.test + k.stok_tasima


def strategy_risk(strateji: Strateji, ana_risk: int) -> float:
    r = [x.uygulama_riski for x in strateji.bilesenler if x.uygulama_riski is not None]
    return float(max(r)) if r else float(ana_risk)


def _norm(v, vals):
    hi, lo = max(vals), min(vals)
    if hi == lo:
        return 1.0, True  # Formuller #44: bölen 0 → 1
    return (hi - v) / (hi - lo), False


def score_mcda(rows: list[dict], w: dict) -> tuple[list[NormalizePuanlar], list[float], list[str]]:
    """rows: {maliyet, durus, co2, risk}. Düşük olan iyi."""
    uyarilar, normlar, skorlar = [], [], []
    for r in rows:
        n = {}
        for k in ("maliyet", "durus", "co2", "risk"):
            n[k], tanimsiz = _norm(r[k], [x[k] for x in rows])
            if tanimsiz and k not in uyarilar:
                uyarilar.append(k)
        normlar.append(NormalizePuanlar(**n))
        skorlar.append(w["maliyet"] * n["maliyet"] + w["durus"] * n["durus"] + w["co2"] * n["co2"] + w["risk"] * n["risk"])
    return normlar, skorlar, uyarilar


def rank_strategies(skorlar: list[float]) -> list[int]:
    """Formuller #46."""
    return [1 + sum(1 for o in skorlar if o > s + 1e-12) for s in skorlar]
