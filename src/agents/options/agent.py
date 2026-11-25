"""Options Agent (04): Sourcing + Logistics alt modülleri → OptionsOutput.

Tüm sayı tool'lardan gelir (OP-K5). Sıralama / öneri yok (OP-K6).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from src.contracts.schemas import (ElenenKaynak, ImpactOutput, KaynakRef, KisitKontrolu, OptionsOutput,
                                   RiskOutput, Strateji, StratejiBileseni, Uyari)
from src.data_access.loader import NexusData
from src.agents.options.sourcing import tools as src_t
from src.agents.options.logistics import tools as log_t


def _now():
    return datetime.now(timezone.utc)


def _bilesen(no, tip, kaynak, rota, miktar, olcu, brut, hazir, loj, ek, test, co2, risk, kalan, kontroller):
    return StratejiBileseni(
        bilesen_no=no, tip=tip, kaynak=kaynak, rota_kodu=rota["Rota Kodu"] if rota else None,
        miktar=miktar, olcu_birimi=olcu, brut_kg=round(brut, 6), hazir_gun=hazir,
        lojistik_maliyet_try=round(loj, 4), ek_malzeme_maliyeti_try=round(ek, 4), test_maliyeti_try=test,
        co2_kg=round(co2, 6), uygulama_riski=risk,
        kisit_kontrolu=KisitKontrolu(sonuc="KALDI" if kalan else "GEÇTİ", kontroller=kontroller, kalan_kisitlar=kalan))


def _strateji(kod, ad, bilesenler):
    kaldi = [b for b in bilesenler if b.kisit_kontrolu.sonuc == "KALDI"]
    neden = None
    if kaldi:
        neden = "Kısıt kaldı: " + ", ".join(f"bileşen {b.bilesen_no} ({'/'.join(b.kisit_kontrolu.kalan_kisitlar)})" for b in kaldi)
    return Strateji(strateji_kodu=kod, strateji_adi=ad, bilesenler=bilesenler, uygun_mu=not kaldi, eleme_nedeni=neden)


def run(data: NexusData, signal: Any, impact: ImpactOutput, risk: Optional[RiskOutput], run_id: str) -> OptionsOutput:
    t0 = _now()
    uyarilar: list[Uyari] = []
    kaynak_ref: dict[str, set] = {}

    def ref(sayfa, anahtar):
        kaynak_ref.setdefault(sayfa, set()).add(anahtar)

    mat_no, tesis = impact.malzeme_no, impact.tesis_kodu
    mat = src_t.material(data, mat_no)
    ref("Malzemeler", mat_no)
    olcu = impact.olcu_birimi or mat.get("Ölçü Birimi")
    usdtry = float(data.param("USDTRY"))
    tampon = float(data.param("PlanlamaTamponu"))
    H = float(impact.kullanilabilir_gun)
    d, S0 = float(impact.gunluk_tuketim), float(impact.serbest_stok)
    gumruk = float(mat.get("Gümrük Süresi (gün)") or 0)
    kalite = float(mat.get("Giriş Kalite Serbest Bırakma (gün)") or 0)
    pre = impact.senaryo or "S1"

    # ---- a) Transfer ----
    transfer_bil = None
    trs = src_t.find_transfer_sources(data, mat_no, tesis)
    for tr in trs:
        ref("Stok_Durumu", tr["stok_anahtari"])
        if not tr["formul_tutarli"]:
            uyarilar.append(Uyari(kod="HAZIR_DEGER_FARKI", mesaj=f"{tr['stok_anahtari']} transfer edilebilir miktar formülle tutarsız",
                                  alan="Transfer Edilebilir Miktar"))
        rotalar = log_t.list_routes(data, tesis, cikis_tesis=tr["tesis"])
        if not rotalar:
            continue
        rota = rotalar[0]
        ref("Rota_Secenekleri", rota["Rota Kodu"])
        brut = log_t.brut_kg(data, mat_no, tr["miktar"])
        hazir = log_t.compute_ready_day(0, 0, float(rota["Kapı-Kapı Süre (gün)"]), 0, 0)
        kalan = [] if tr["miktar"] <= tr["miktar"] + 1e-6 else ["C1"]
        if not log_t.capacity_ok(rota, brut):
            kalan.append("C6")
        transfer_bil = dict(tip="TRANSFER", kaynak=f"{tr['tesis']}|{mat_no}", rota=rota, miktar=tr["miktar"], brut=brut,
                            hazir=hazir, loj=log_t.compute_logistics_cost(data, rota, brut), ek=0.0, test=0.0,
                            co2=log_t.compute_co2(rota, brut), risk=log_t.route_risk(data, rota), kalan=kalan,
                            kontroller=["C1", "C6"])
        break
    if transfer_bil is None:
        uyarilar.append(Uyari(kod="EKSIK_BILESEN", mesaj="Transfer kaynağı/rotası bulunamadı; transfer stratejisi üretilmedi"))

    # ---- b) Alternatif tedarikçi + c) rota ----
    elenen: list[ElenenKaynak] = []
    alt = None
    for k in src_t.list_alt_suppliers(data, mat_no):
        ref("Tedarik_Kaynaklari", k["Kaynak Anahtarı"])
        q = src_t.check_qualification(data, k)
        rotalar = log_t.list_routes(data, tesis, cikis_lokasyon=k.get("Çıkış Lokasyonu"))
        kapi = float(rotalar[0]["Kapı-Kapı Süre (gün)"]) if rotalar else 0.0
        hazir = log_t.compute_ready_day(float(k.get("Acil Sevk Hazırlık (gün)") or 0), q["kalif_gun"], kapi, gumruk, kalite)
        if not q["gecti"]:
            elenen.append(ElenenKaynak(kaynak=k["Kaynak Anahtarı"], neden=q["neden"], hazir_gun=hazir))
            continue
        if not rotalar:
            elenen.append(ElenenKaynak(kaynak=k["Kaynak Anahtarı"], neden="Tesise uygun rota bulunamadı"))
            continue
        if alt is None:
            alt = (k, rotalar[0], hazir)
    if alt is None:
        uyarilar.append(Uyari(kod="EKSIK_BILESEN", mesaj="Uygun alternatif tedarikçi bulunamadı"))

    def alt_bil(miktar):
        k, rota, hazir = alt
        ref("Rota_Secenekleri", rota["Rota Kodu"])
        brut = log_t.brut_kg(data, mat_no, miktar)
        kalan = src_t.check_supply_constraints(k, miktar, H - hazir)
        if not log_t.capacity_ok(rota, brut):
            kalan.append("C6")
        dahil = k.get("Navlun Fiyata Dahil mi?") == "Evet"
        return dict(tip="ALTERNATIF_TEDARIK_ROTA", kaynak=k["Kaynak Anahtarı"], rota=rota, miktar=miktar, brut=brut,
                    hazir=hazir, loj=log_t.compute_logistics_cost(data, rota, brut, dahil),
                    ek=src_t.extra_material_cost_try(data, k, miktar), test=src_t.test_cost_try(data, mat_no),
                    co2=log_t.compute_co2(rota, brut), risk=log_t.route_risk(data, rota), kalan=kalan,
                    kontroller=["C2", "C3", "C4", "C5", "C6"])

    # ---- c) Rota değişikliği (COD) ----
    cod_bil = None
    sev = next((r for r in data.rows("Sevkiyatlar") if r["Sevkiyat No"] == impact.sevkiyat_no), None)
    if sev:
        ref("Sevkiyatlar", impact.sevkiyat_no)
        cods = log_t.list_routes(data, tesis, mod="COD")
        if cods:
            rota = cods[0]
            ref("Rota_Secenekleri", rota["Rota Kodu"])
            brut = float(sev.get("Brüt Ağırlık (kg)") or log_t.brut_kg(data, mat_no, sev["Miktar"]))
            hazir = log_t.compute_ready_day(0, 0, float(rota["Kapı-Kapı Süre (gün)"]), float(sev.get("Gümrük (gün)") or 0),
                                            float(sev.get("Kalite Serbest Bırakma (gün)") or 0), float(impact.what_if_gun or 0))
            cod_bil = dict(tip="ROTA_DEGISIKLIGI", kaynak=impact.sevkiyat_no, rota=rota, miktar=float(sev["Miktar"]),
                           brut=brut, hazir=hazir, loj=log_t.compute_logistics_cost(data, rota, brut), ek=0.0, test=0.0,
                           co2=log_t.compute_co2(rota, brut), risk=log_t.route_risk(data, rota),
                           kalan=[] if log_t.capacity_ok(rota, brut) else ["C6"], kontroller=["C6"])

    def mk(kod, ad, parts):
        return _strateji(f"{pre}-{kod}", ad, [_bilesen(i + 1, p["tip"], p["kaynak"], p["rota"], p["miktar"], olcu, p["brut"],
                                                       p["hazir"], p["loj"], p["ek"], p["test"], p["co2"], p["risk"],
                                                       p["kalan"], p["kontroller"]) for i, p in enumerate(parts)])

    stratejiler = [Strateji(strateji_kodu=f"{pre}-AKS", strateji_adi="Hiçbir şey yapma (bekle)", bilesenler=[], uygun_mu=True)]
    if transfer_bil:
        stratejiler.append(mk("TRF", "Sadece depodan transfer", [transfer_bil]))
    if alt:
        k = alt[0]
        moq = float(k.get("Spot MOQ (birim)") or 0)
        q_k = src_t.compute_hybrid_qty(H, tampon, d, S0, 0.0, moq)
        stratejiler.append(mk("KHV", "Sadece kısmi uçak (alternatif tedarikçi)", [alt_bil(q_k)]))
        hazir_stok = float(k.get("Hazır Stok (birim)") or 0)
        if hazir_stok > q_k:
            stratejiler.append(mk("THV", "Tamamını uçakla getir (alternatif tedarikçi)", [alt_bil(hazir_stok)]))
    if cod_bil:
        ipucu = getattr(signal, "alternatif_ipucu", None) if signal is not None else None
        stratejiler.append(mk("COD", "Gemiyi alternatif limana yönlendir (COD)" + (f" – ipucu: {ipucu}" if ipucu else ""), [cod_bil]))
    if transfer_bil and alt:
        moq = float(alt[0].get("Spot MOQ (birim)") or 0)
        q_h = src_t.compute_hybrid_qty(H, tampon, d, S0, transfer_bil["miktar"], moq)
        stratejiler.append(mk("HIB", "Depodan transfer + uçakla kısmi tedarik (hibrit)", [transfer_bil, alt_bil(q_h)]))

    if not any(s.uygun_mu and s.bilesenler for s in stratejiler):
        uyarilar.append(Uyari(kod="UYGUN_STRATEJI_YOK", mesaj="Yalnızca 'Bekle' stratejisi uygun"))
    ref("Parametreler", "USDTRY")

    return OptionsOutput(
        run_id=run_id, senaryo=impact.senaryo, risk_no=impact.risk_no or (risk.risk_no if risk else None),
        d0=data.d0, what_if_gun=impact.what_if_gun, baslangic_zamani=t0, bitis_zamani=_now(),
        durum="UYARI" if uyarilar else "TAMAM", uyarilar=uyarilar, stratejiler=stratejiler, elenen_kaynaklar=elenen,
        kaynak=[KaynakRef(sayfa=s, anahtarlar=sorted(a)) for s, a in kaynak_ref.items()])
