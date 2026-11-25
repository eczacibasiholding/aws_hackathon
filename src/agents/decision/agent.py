"""Decision Agent (05): simülasyon → maliyet → ÇKKV → (S1) MILP → öneri kartı + karar kaydı taslağı.

Tüm rakamlar tool'lardan gelir; LLM yalnızca DecisionMetinLLM'i doldurur (DC-K2) ve rakam testinden geçemezse
deterministik şablon kullanılır.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Optional

from src.common import llm
from src.contracts.schemas import (DecisionMetinLLM, DecisionOutput, ImpactOutput, KararKaydiTaslagi, MilpSonucu,
                                   OneriKarti, OneriRakamlari, OptionsOutput, RiskOutput, StratejiKarsilastirma, Uyari)
from src.data_access.loader import NexusData
from src.agents.decision.prompts.gerekce import SYSTEM
from src.agents.decision.tools import milp as milp_t
from src.agents.decision.tools import rationale as rat
from src.agents.decision.tools import scoring as sc
from src.agents.decision.tools.simulation import simulate_inventory

SOURCING = {"TRANSFER", "ALTERNATIF_TEDARIK_ROTA"}
LOGISTICS = {"ROTA_DEGISIKLIGI", "ALTERNATIF_TEDARIK_ROTA"}


def _now():
    return datetime.now(timezone.utc)


def _row(data, sheet, key, val):
    return next((r for r in data.rows(sheet) if r.get(key) == val), None)


def _ana_rota_riski(data: NexusData, sev: Optional[dict], tesis: str) -> int:
    """Bekle stratejisinin riski: ana sevkiyatın planlı rotasının uygulama riski."""
    if sev:
        for r in data.rows("Rota_Secenekleri"):
            if (r.get("Taşıyıcı No") == sev.get("Taşıyıcı No") and tesis in str(r.get("Varış"))
                    and not r["Rota Kodu"].startswith("R-COD")):
                return int(r["Uygulama Riski (1-5)"])
    return 3


def _olay_tipi(strateji) -> Optional[str]:
    if strateji is None or not strateji.bilesenler:
        return None
    tipler = {b.tip for b in strateji.bilesenler}
    s, l = bool(tipler & SOURCING), bool(tipler & LOGISTICS)
    return "Birleşik (Tedarik + Lojistik)" if s and l else ("Tedarik" if s else "Lojistik")


def _milp_params(data: NexusData, options: OptionsOutput, impact: ImpactOutput) -> Optional[dict]:
    trf = alt = cod = None
    for s in options.stratejiler:
        if not s.uygun_mu:
            continue
        for b in s.bilesenler:
            if b.tip == "TRANSFER" and trf is None:
                trf = b
            elif b.tip == "ALTERNATIF_TEDARIK_ROTA" and alt is None:
                alt = b
            elif b.tip == "ROTA_DEGISIKLIGI" and cod is None:
                cod = b
    if trf is None or alt is None:
        return None
    usdtry = float(data.param("USDTRY"))
    k = _row(data, "Tedarik_Kaynaklari", "Kaynak Anahtarı", alt.kaynak)
    rota = _row(data, "Rota_Secenekleri", "Rota Kodu", alt.rota_kodu)
    mat = _row(data, "Malzemeler", "Malzeme No", impact.malzeme_no)
    if not (k and rota and mat):
        return None
    brut_birim = float(mat["Brüt Ağırlık (kg/birim)"])
    fark = alt.ek_malzeme_maliyeti_try / alt.miktar / usdtry   # Formuller #31 (Options tool'u)
    dahil = k.get("Navlun Fiyata Dahil mi?") == "Evet"
    c_A = (fark + (0 if dahil else brut_birim * float(rota["Değişken Maliyet (USD/kg)"]))) * usdtry  # Formuller #48
    F_A = (0 if dahil else float(rota["Sabit Maliyet (USD/sevkiyat)"]) * usdtry) + alt.test_maliyeti_try
    return {"S0": impact.serbest_stok, "d": impact.gunluk_tuketim, "t_b": impact.kullanilabilir_gun,
            "t_c": cod.hazir_gun if cod else None, "B": float(data.param("PlanlamaTamponu")),
            "pen": impact.gunluk_durus_maliyeti_try, "R": impact.yeniden_baslatma_maliyeti_try,
            "T_max": trf.miktar, "A_max": float(k.get("Hazır Stok (birim)") or 0)
            + float(k.get("Ek Üretim Kapasitesi (birim/gün)") or 0) * max(0.0, impact.kullanilabilir_gun - alt.hazir_gun),
            "MOQ": float(k.get("Spot MOQ (birim)") or 0), "c_A": c_A, "F_A": F_A, "F_T": trf.lojistik_maliyet_try,
            "F_C": cod.lojistik_maliyet_try if cod else 0.0, "a_T": trf.hazir_gun, "a_A": alt.hazir_gun, "M": 10000}


def run(data: NexusData, signal: Any, impact: ImpactOutput, risk: Optional[RiskOutput], options: OptionsOutput,
        run_id: str) -> DecisionOutput:
    t0 = _now()
    uyarilar: list[Uyari] = []
    sev = _row(data, "Sevkiyatlar", "Sevkiyat No", impact.sevkiyat_no)
    mat = _row(data, "Malzemeler", "Malzeme No", impact.malzeme_no) or {}
    ana_miktar = float(sev["Miktar"]) if sev else 0.0
    birim_try = float(mat.get("Birim Maliyet (TRY)") or 0)
    oran = float(data.param("StokTasimaOrani"))
    ana_risk = _ana_rota_riski(data, sev, impact.tesis_kodu)
    w = {"maliyet": float(data.param("W_Maliyet")), "durus": float(data.param("W_Durus")),
         "co2": float(data.param("W_CO2")), "risk": float(data.param("W_Risk"))}

    # 1–2: simülasyon + maliyet
    simler, satirlar = [], []
    for s in options.stratejiler:
        sim, durus = simulate_inventory(s, impact.serbest_stok, impact.gunluk_tuketim, impact.kullanilabilir_gun, ana_miktar)
        simler.append(sim)
        kal = sc.compute_total_cost(s, durus, impact, birim_try, oran)
        satirlar.append({"s": s, "durus": durus, "kal": kal, "maliyet": sc.total(kal),
                         "co2": sum(b.co2_kg for b in s.bilesenler), "risk": sc.strategy_risk(s, ana_risk)})

    # 3: ÇKKV (yalnızca uygun stratejiler)
    uygun = [r for r in satirlar if r["s"].uygun_mu]
    normlar, skorlar, tanimsiz = sc.score_mcda(uygun, w) if uygun else ([], [], [])
    for k in tanimsiz:
        uyarilar.append(Uyari(kod="NORMALIZE_TANIMSIZ", mesaj=f"'{k}' kriterinde en iyi = en kötü; normalize 1 alındı",
                              alan=f"normalize.{k}"))
    siralar = sc.rank_strategies(skorlar)
    for r, n, sk, sr in zip(uygun, normlar, skorlar, siralar):
        r.update(norm=n, skor=sk, sira=sr)
    birinci = [r for r in uygun if r.get("sira") == 1]
    oneri = birinci[0] if birinci else None
    if not uygun or (oneri and not oneri["s"].bilesenler and len(uygun) == 1):
        uyarilar.append(Uyari(kod="UYGUN_STRATEJI_YOK", mesaj="Kısıtı geçen aksiyon stratejisi yok"))

    karsilastirma = []
    for r in satirlar:
        karsilastirma.append(StratejiKarsilastirma(
            strateji_kodu=r["s"].strateji_kodu, strateji_adi=r["s"].strateji_adi, uygun_mu=r["s"].uygun_mu,
            durus_gun=round(r["durus"], 9), maliyet_kalemleri=r["kal"], toplam_maliyet_try=r["maliyet"], co2_kg=r["co2"],
            risk=r["risk"], normalize=r.get("norm") or {}, agirlikli_skor=r.get("skor"), sira=r.get("sira"),
            oneri="ÖNERİLEN" if r is oneri else None))

    # 4: MILP (S1)
    milp_out = None
    dikkat = None
    if options.senaryo == "S1" or impact.senaryo == "S1":
        p = _milp_params(data, options, impact)
        sol = milp_t.solve_milp(p) if p else None
        if not sol or sol["durum"] != "OPTIMAL":
            uyarilar.append(Uyari(kod="MILP_YAPILAMADI", mesaj="MILP doğrulaması yapılamadı; ÇKKV sonucu sunuluyor", alan="milp"))
            if sol:
                milp_out = MilpSonucu(durum=sol["durum"])
        else:
            uyum = None
            if oneri:
                tip = {b.tip for b in oneri["s"].bilesenler}
                uyum = ((sol["x_T"] > 1e-6) == ("TRANSFER" in tip) and (sol["x_A"] > 1e-6) == ("ALTERNATIF_TEDARIK_ROTA" in tip)
                        and bool(sol["y_C"]) == ("ROTA_DEGISIKLIGI" in tip))
                if not uyum:
                    dikkat = "MILP çözümü ÇKKV önerisinden farklı bir bileşen bileşimi seçti; öneri değiştirilmedi."
                    uyarilar.append(Uyari(kod="CELISKI", mesaj=dikkat, alan="milp.cckv_ile_uyumlu"))
            milp_out = MilpSonucu(durum="OPTIMAL", x_T=round(sol["x_T"], 6), x_A=round(sol["x_A"], 6), y_C=sol["y_C"],
                                  amac_try=round(sol["amac_try"], 4), cckv_ile_uyumlu=uyum)

    # 5–6: kart + gerekçe
    aks = impact.aksiyonsuz_maliyet_try
    rak = OneriRakamlari(durus_gun=oneri["durus"] if oneri else impact.acik_durus_gun,
                         toplam_maliyet_try=oneri["maliyet"] if oneri else aks, aksiyonsuz_maliyet_try=aks,
                         tasarruf_try=(aks - oneri["maliyet"]) if oneri else 0.0)
    ctx = {"onerilen_ad": oneri["s"].strateji_adi if oneri else None, "tukenme": impact.tukenme_tarihi,
           "kullanilabilir": impact.guncel_kullanilabilir_tarih, "durus": rak.durus_gun, "toplam": rak.toplam_maliyet_try,
           "aksiyonsuz": aks, "tasarruf": rak.tasarruf_try, "sevkiyat_no": impact.sevkiyat_no,
           "malzeme_no": impact.malzeme_no, "acik": impact.acik_durus_gun}
    ikinci = sorted([r for r in uygun if r is not oneri], key=lambda r: r["sira"])[:1]
    izinli_vals = [rak.durus_gun, rak.toplam_maliyet_try, aks, rak.tasarruf_try, impact.acik_durus_gun,
                   impact.stok_kapsama_gun, impact.kullanilabilir_gun, impact.serbest_stok, impact.gunluk_tuketim,
                   risk.risk_puani if risk else None]
    if oneri:
        izinli_vals += [b.miktar for b in oneri["s"].bilesenler] + [b.hazir_gun for b in oneri["s"].bilesenler]
    if ikinci:
        izinli_vals += [ikinci[0]["maliyet"], ikinci[0]["durus"], ikinci[0]["maliyet"] - rak.toplam_maliyet_try]
    for kod in (impact.sevkiyat_no, impact.malzeme_no, impact.tesis_kodu, impact.hat_kodu, impact.risk_no or ""):
        izinli_vals += [float(x) for x in re.findall(r"\d+", kod)]
    izinli = rat.allowed_numbers(izinli_vals, [impact.tukenme_tarihi, impact.guncel_kullanilabilir_tarih, data.d0])

    sablon_g, sablon_oz = rat.template(ctx)
    olay_tipi = _olay_tipi(oneri["s"] if oneri else None)
    gerekce, olay_ozeti = sablon_g, sablon_oz
    llm_ctx = {**{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in ctx.items()},
               "bilesenler": [b.model_dump(include={"tip", "kaynak", "rota_kodu", "miktar", "hazir_gun"})
                              for b in (oneri["s"].bilesenler if oneri else [])],
               "ikinci_strateji": ({"ad": ikinci[0]["s"].strateji_adi, "toplam": ikinci[0]["maliyet"]} if ikinci else None),
               "risk_kademesi": risk.risk_kademesi if risk else None, "milp_cckv_uyumlu": milp_out.cckv_ile_uyumlu if milp_out else None,
               "dikkat_notu_taslak": dikkat}
    metin = llm.structured("Bağlam (JSON):\n" + json.dumps(llm_ctx, ensure_ascii=False, default=str),
                           DecisionMetinLLM, SYSTEM)
    if metin is None:
        uyarilar.append(Uyari(kod="LLM_HATA", mesaj="LLM gerekçesi üretilemedi; deterministik şablon kullanıldı",
                              alan="oneri_karti.gerekce"))
    elif all(rat.number_test(t, izinli) for t in (metin.gerekce, metin.dikkat_notu, getattr(metin, "olay_ozeti", None))):
        gerekce = metin.gerekce
        dikkat = metin.dikkat_notu or dikkat
        olay_ozeti = getattr(metin, "olay_ozeti", None) or sablon_oz
        olay_tipi = getattr(metin, "olay_tipi", None) or olay_tipi
    else:
        uyarilar.append(Uyari(kod="LLM_HATA", mesaj="Gerekçe rakam testini geçemedi; deterministik şablon kullanıldı",
                              alan="oneri_karti.gerekce"))

    kart = OneriKarti(
        baslik=f"Önerilen: {oneri['s'].strateji_adi}" if oneri else "Uygun strateji bulunamadı",
        gerekce=gerekce, dikkat_notu=dikkat, onerilen_strateji_kodu=oneri["s"].strateji_kodu if oneri else None,
        rakamlar=rak, olay_tipi=olay_tipi, olay_ozeti=olay_ozeti)
    t1 = _now()
    taslak = KararKaydiTaslagi(olay_no="NXS-26-025", tasarruf_try=rak.tasarruf_try if oneri else None, oneri_zamani=t1)

    return DecisionOutput(
        run_id=run_id, senaryo=options.senaryo, risk_no=options.risk_no, d0=data.d0, what_if_gun=impact.what_if_gun,
        baslangic_zamani=t0, bitis_zamani=_now(), durum="UYARI" if uyarilar else "TAMAM", uyarilar=uyarilar,
        simulasyon=simler, karsilastirma=karsilastirma, milp=milp_out, oneri_karti=kart, karar_kaydi_taslagi=taslak)
