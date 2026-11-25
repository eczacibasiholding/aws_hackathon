"""01 · Signal Agent: ham sinyal metni → SignalOutput.

LLM yalnızca SignalLLMCikarimi doldurur; eşleştirme, güvenilirlik, gürültü filtresi ve gruplama deterministiktir.
"""
from __future__ import annotations

from datetime import datetime

from src.common import llm
from src.contracts.schemas import KaynakRef, SignalKanit, SignalLLMCikarimi, SignalOutput, Uyari

from .prompts import SYSTEM, kullanici_prompt
from .tools.extraction import cumleler, deterministik_cikarim
from .tools import matching as m

METIN = "Ham Metin (LLM Girdisi)"


def _tum(data) -> list[dict]:
    return list(data.rows("Risk_Sinyalleri")) + list(getattr(data, "extra_signals", []) or [])


def list_signals(data) -> list[str]:
    return [str(r["Sinyal No"]) for r in _tum(data)]


def _satir(data, sinyal_no: str) -> dict:
    for r in _tum(data):
        if str(r["Sinyal No"]) == sinyal_no:
            return r
    raise KeyError(f"Sinyal bulunamadı: {sinyal_no}")


def _taraf_adlari(data) -> list[str]:
    return [r["Tedarikçi Adı (Sahte)"] for r in data.rows("Tedarikciler")] + \
           [r["Taşıyıcı Adı (Sahte)"] for r in data.rows("Tasiyicilar")]


def cikar(data, row: dict) -> tuple[SignalLLMCikarimi, list[Uyari]]:
    metin = str(row.get(METIN) or "")
    c = llm.structured(kullanici_prompt(row["Sinyal No"], row.get("Dil"), row.get("Kategori"), metin),
                       SignalLLMCikarimi, SYSTEM)
    if c is not None:
        return c, []
    c = deterministik_cikarim(metin, _taraf_adlari(data), data.d0.year)
    if c.olay_tipi is None and row.get("Kategori"):
        c.olay_tipi = row.get("Kategori")
    return c, [Uyari(kod="LLM_HATA", mesaj="LLM kullanılamadı; deterministik regex çıkarımı kullanıldı")]


def run(data, sinyal_no: str, run_id: str) -> SignalOutput:
    bas = datetime.now()
    row = _satir(data, sinyal_no)
    metin = str(row.get(METIN) or "")
    c, uyarilar = cikar(data, row)
    sev, mlz, taraf, yol = m.eslestir(data, c, metin)
    dogr: list[Uyari] = []
    if not sev and (c.takip_no_ipuclari or c.po_ipuclari or c.gemi_adlari):
        dogr.append(Uyari(kod="ESLESME_YOK", mesaj="Metindeki ipuçları hiçbir sevkiyatla eşleşmedi",
                          alan="ilgili_sevkiyat"))
    if len(sev) > 1:
        dogr.append(Uyari(kod="COKLU_ADAY", mesaj=f"Birden çok sevkiyat: {sev}", alan="ilgili_sevkiyat"))
    cel = m.gecikme_capraz(data, sev, c.tahmini_gecikme_gun)
    if cel:
        dogr.append(Uyari(kod="CELISKI", mesaj=cel, alan="tahmini_gecikme_gun"))
    neden = m.gurultu_nedeni(row, sev)
    alintilar = [a for a in c.alintilar.values() if a and a in metin]
    if not alintilar:
        anahtarlar = c.takip_no_ipuclari + c.po_ipuclari + c.gemi_adlari
        alintilar = [s for s in cumleler(metin) if any(k in s for k in anahtarlar)] or cumleler(metin)[:1]
    kaynak = [KaynakRef(sayfa="Risk_Sinyalleri", anahtarlar=[sinyal_no], sutunlar=[METIN])]
    if sev:
        kaynak.append(KaynakRef(sayfa="Sevkiyatlar", anahtarlar=sev,
                                sutunlar=["Takip No (Sahte)", "PO No", "Son Konum / Not", "Malzeme No"]))
    tum_uyari = uyarilar + dogr
    return SignalOutput(
        run_id=run_id, d0=data.d0, what_if_gun=float(data.params.get("WhatIfGun", 0) or 0),
        baslangic_zamani=bas, bitis_zamani=datetime.now(),
        durum="UYARI" if tum_uyari else "TAMAM", uyarilar=uyarilar,
        sinyal_no=sinyal_no, isleme_karari="AYIKLA" if neden else "ANALIZ", ayiklama_nedeni=neden,
        olay_tipi=c.olay_tipi, ulke_bolge=c.ulke_bolge, ilgili_taraf=taraf,
        ilgili_sevkiyat=sev, ilgili_malzeme=mlz, tahmini_gecikme_gun=c.tahmini_gecikme_gun,
        alternatif_ipucu=c.alternatif_ipucu, sinyal_guvenilirligi=m.guvenilirlik(data, row),
        tespit_gecikmesi_saat=m.tespit_gecikmesi_saat(row),
        kanit=SignalKanit(metin_alintilari=alintilar, eslesme_yolu="; ".join(yol) or None),
        kaynak=kaynak, dogrulama_uyarilari=dogr,
    )


def group_signals(data, run_id: str = "group") -> dict[str, str]:
    """ANALIZ sinyallerini ilk eşleşen sevkiyata göre gruplar (sinyal → grup anahtarı)."""
    outs = {s: run(data, s, run_id) for s in list_signals(data)}
    return m.grupla({s: o.ilgili_sevkiyat for s, o in outs.items() if o.isleme_karari == "ANALIZ"})
