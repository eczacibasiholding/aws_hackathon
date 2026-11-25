"""03 · Impact Agent — "Malzeme ne zaman kullanılabilir, stok kaç gün yeter, aksiyonsuz maliyet ne?"

Arayüz: run(data, signal, run_id, what_if_gun=None) -> list[ImpactOutput]
  - Sevkiyat × hat başına bir çıktı (çoklu eşleşmede hepsi ayrı hesaplanır, kapsam md §4.2).
  - Tüm sayılar tools/calc.py'den gelir; LLM sayı üretmez (I-K1). Bu agent'ta LLM adımı yoktur;
    tutarlılık kontrolleri deterministik yapılır ve uyarıya yazılır (sayı düzeltilmez).
  - what_if_gun None ise Parametreler → WhatIfGun, yalnızca signal.senaryo == WhatIfSenaryo ise uygulanır (I-K4).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from src.contracts.schemas import ImpactOutput, KaynakRef, RiskAltindakiSiparis, SignalOutput, Uyari
from src.agents.impact.tools import calc

log = logging.getLogger("nexus.impact")
TOL_GUN = 0.01
TOL_TRY = 1.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _what_if(data, signal: SignalOutput, override: Optional[float]) -> float:
    if override is not None:
        return float(override)
    try:
        if signal.senaryo and signal.senaryo == data.param("WhatIfSenaryo"):
            return float(data.param("WhatIfGun") or 0)
    except KeyError:
        pass
    return 0.0


def _birim(v) -> Optional[str]:
    v = (str(v).strip().upper() if v else None)
    return v if v in {"KG", "TON", "ADET"} else None


def run(data, signal: SignalOutput, run_id: str, what_if_gun: Optional[float] = None) -> list[ImpactOutput]:
    baslangic = _now()
    wi = _what_if(data, signal, what_if_gun)
    ciktilar: list[ImpactOutput] = []
    for sevkiyat_no in signal.ilgili_sevkiyat:
        ciktilar.extend(_shipment(data, signal, run_id, sevkiyat_no, wi, baslangic))
    if not ciktilar:
        log.warning("Impact: %s için hesaplanabilir kayıt yok", signal.sinyal_no)
    return ciktilar


def _shipment(data, signal, run_id, sevkiyat_no, wi, baslangic) -> list[ImpactOutput]:
    ch = calc.resolve_chain(data, sevkiyat_no)
    sv, stok = ch["sevkiyat"], ch.get("stok")
    if sv is None or stok is None or not ch.get("hatlar"):
        # Kapsam md §7: stok anahtarı yok → HATA; ImpactOutput zorunlu alanları doldurulamadığından çıktı üretilmez.
        log.error("Impact zinciri kurulamadı: %s (stok=%s, hat=%s)", sevkiyat_no,
                  stok is not None, bool(ch.get("hatlar")))
        return []
    if signal.ilgili_malzeme and sv["Malzeme No"] not in signal.ilgili_malzeme:
        log.warning("%s malzemesi %s sinyal malzemeleri arasında değil", sevkiyat_no, sv["Malzeme No"])

    d0 = data.d0
    out = []
    for hat in ch["hatlar"]:
        uy: list[Uyari] = []
        serbest = float(stok.get("Serbest Stok") or 0)
        tuketim_girdi = float(stok.get("Günlük Tüketim") or 0)
        ihtiyac = calc.compute_daily_need(hat)
        if tuketim_girdi and abs(ihtiyac - tuketim_girdi) > 0.01:
            uy.append(Uyari(kod="HAZIR_DEGER_FARKI", alan="gunluk_tuketim",
                            mesaj=f"Hesaplanan günlük ihtiyaç {ihtiyac:.3f} ≠ Stok_Durumu.Günlük Tüketim {tuketim_girdi}"))
        tuketim = tuketim_girdi or ihtiyac
        if not tuketim_girdi:
            uy.append(Uyari(kod="EKSIK_BILESEN", alan="gunluk_tuketim",
                            mesaj="Stok_Durumu.Günlük Tüketim 0/boş; hat ihtiyacı (I1) kullanıldı"))
        kapsama = calc.compute_coverage(serbest, tuketim)
        tukenme = calc.compute_depletion(d0, kapsama)
        plan = calc.compute_usable_date(sv, "Planlanan Varış (ETA)")
        guncel = calc.compute_usable_date(sv, "Güncel Tahmini / Gerçekleşen Varış", wi)
        kgun = calc.day_index(d0, guncel)
        acik = calc.compute_gap(kgun, kapsama)

        gunluk_girdi = float(hat.get("Günlük Duruş Maliyeti (TRY)") or 0)
        gunluk_hesap = calc.compute_daily_downtime_cost(hat)
        if abs(gunluk_girdi - gunluk_hesap) > TOL_TRY:
            uy.append(Uyari(kod="HAZIR_DEGER_FARKI", alan="gunluk_durus_maliyeti_try",
                            mesaj=f"Hesaplanan günlük duruş {gunluk_hesap:.0f} ≠ girdi {gunluk_girdi:.0f}; girdi kullanıldı (I9)"))
        gunluk = gunluk_girdi or gunluk_hesap
        restart = float(hat.get("Yeniden Başlatma Maliyeti (TRY)") or 0)
        durus = calc.compute_downtime_cost(acik, gunluk, restart)

        siparisler = []
        if acik > 0:
            for o in calc.find_orders_at_risk(calc.orders_for_line(data, hat["Hat Kodu"]), tukenme, guncel):
                gec, ceza = calc.compute_penalty(o, guncel)
                siparisler.append(RiskAltindakiSiparis(
                    siparis_no=o["Sipariş No"], hat_kodu=o["Hat Kodu"],
                    gerekli_uretim_tarihi=calc._to_date(o["Gerekli Üretim Tarihi"]),
                    gecikme_gun=gec, gunluk_ceza_try=o.get("Gecikme Cezası (TRY/gün)"), ceza_try=ceza))
        ceza_top = sum(s.ceza_try for s in siparisler)
        aksiyonsuz = durus + ceza_top

        emniyet = stok.get("Emniyet Stoğu (gün)")
        etki = calc.compute_impact_score(acik, aksiyonsuz, float(data.param("EtkiMaliyetYuksek")),
                                         float(data.param("EtkiMaliyetOrta")), kapsama - kgun,
                                         None if emniyet is None else float(emniyet))

        # Süre tutarlılığı (Malzemeler) ve birim kontrolü
        mz = ch.get("malzeme") or {}
        for sv_col, mz_col in (("Gümrük (gün)", "Gümrük Süresi (gün)"),
                               ("Kalite Serbest Bırakma (gün)", "Giriş Kalite Serbest Bırakma (gün)")):
            a, b = sv.get(sv_col), mz.get(mz_col)
            if a is not None and b is not None and float(a) != float(b):
                uy.append(Uyari(kod="HAZIR_DEGER_FARKI", alan="guncel_kullanilabilir_tarih",
                                mesaj=f"Sevkiyatlar.{sv_col}={a} ≠ Malzemeler.{mz_col}={b}; Sevkiyatlar kullanıldı"))
        if _birim(sv.get("Ölçü Birimi")) != _birim(stok.get("Ölçü Birimi")):
            uy.append(Uyari(kod="BIRIM_UYUMSUZ", alan="olcu_birimi",
                            mesaj=f"Sevkiyat birimi {sv.get('Ölçü Birimi')} ≠ stok birimi {stok.get('Ölçü Birimi')}"))

        out.append(ImpactOutput(
            run_id=run_id, senaryo=signal.senaryo, risk_no=signal.risk_no or signal.bagli_risk_no,
            d0=d0, what_if_gun=wi, baslangic_zamani=baslangic, bitis_zamani=_now(),
            durum="UYARI" if uy else "TAMAM", uyarilar=uy,
            sevkiyat_no=sv["Sevkiyat No"], malzeme_no=sv["Malzeme No"], tesis_kodu=stok["Tesis Kodu"],
            hat_kodu=hat["Hat Kodu"], olcu_birimi=_birim(stok.get("Ölçü Birimi")),
            serbest_stok=serbest, gunluk_tuketim=tuketim, stok_kapsama_gun=kapsama,
            tukenme_tarihi=tukenme, planlanan_kullanilabilir_tarih=plan, guncel_kullanilabilir_tarih=guncel,
            kullanilabilir_gun=kgun, acik_durus_gun=acik, gunluk_durus_maliyeti_try=gunluk,
            yeniden_baslatma_maliyeti_try=restart, durus_maliyeti_try=durus,
            risk_altindaki_siparisler=siparisler, olasi_ceza_try=ceza_top,
            aksiyonsuz_maliyet_try=aksiyonsuz, etki_puani=etki,
            kaynak=[
                KaynakRef(sayfa="Sevkiyatlar", anahtarlar=[sv["Sevkiyat No"]]),
                KaynakRef(sayfa="Stok_Durumu", anahtarlar=[ch["stok_anahtari"]], sutunlar=["Serbest Stok", "Günlük Tüketim"]),
                KaynakRef(sayfa="Uretim_Hatlari", anahtarlar=[hat["Hat Kodu"]]),
                KaynakRef(sayfa="Musteri_Siparisleri", anahtarlar=[s.siparis_no for s in siparisler]),
                KaynakRef(sayfa="Parametreler", anahtarlar=["AnalizTarihi", "WhatIfSenaryo", "WhatIfGun",
                                                             "EtkiMaliyetYuksek", "EtkiMaliyetOrta"]),
            ]))
    return out
