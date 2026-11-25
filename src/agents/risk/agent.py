"""02 · Risk Agent — "Risk ne kadar ciddi?"

Arayüz: run(data, signal, impacts, run_id, iliskili_sinyaller=None, dis_kosul=None) -> RiskOutput
  - impacts: Impact çıktıları; etki = en yüksek etki_puani (boşsa None → R-K4: puan/kademe yok).
  - iliskili_sinyaller: aynı riske bağlı diğer SignalOutput'lar (dış koşul kanıtı; opsiyonel).
  - dis_kosul: dışarıdan verilen DisKosulBileseni (test/insan girdisi); verilmezse LLM (Bedrock) belirler.
    LLM kapalı/hatalıysa veya kanıt yetersizse puan=None + uyarı → olasılık None (eksik bileşen).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from src.common import llm
from src.contracts.schemas import (DisKosulBileseni, ImpactOutput, KaynakRef, PerformansBileseni,
                                   RiskBilesenleri, RiskOutput, SignalOutput, Uyari)
from src.agents.risk import prompts
from src.agents.risk.tools import scoring


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _context_signals(data, signal: SignalOutput, iliskili: list[SignalOutput]) -> list[dict]:
    """Ana sinyal + aynı sevkiyata/gemiye/takip no'ya atıf yapan sinyaller (Risk_Sinyalleri)."""
    anahtarlar = set(signal.ilgili_sevkiyat)
    for sv in data.rows("Sevkiyatlar"):
        if sv["Sevkiyat No"] in signal.ilgili_sevkiyat:
            if sv.get("Takip No (Sahte)"):
                anahtarlar.add(str(sv["Takip No (Sahte)"]))
            m = re.match(r"(MV [A-ZÇĞİÖŞÜ ]+?)(?:,|;| yük| \d)", str(sv.get("Son Konum / Not") or ""))
            if m:
                anahtarlar.add(m.group(1).strip())
    hedef = {signal.sinyal_no} | {s.sinyal_no for s in iliskili}
    out = []
    for r in data.rows("Risk_Sinyalleri"):
        metin = str(r.get("Ham Metin (LLM Girdisi)") or "")
        if r["Sinyal No"] in hedef or any(a and a in metin for a in anahtarlar):
            if r["Sinyal No"].endswith("H"):
                continue
            out.append(r)
    return out


def _dis_kosul_llm(data, signal, sinyaller: list[dict], uy: list[Uyari]) -> DisKosulBileseni:
    satirlar = [f"- Ana sinyal {signal.sinyal_no}: olay_tipi={signal.olay_tipi}, bölge={signal.ulke_bolge}"]
    for r in sinyaller:
        satirlar.append(f"- {r['Sinyal No']} (kaynak {r.get('Kaynak Adı')}, doğrulandı={r.get('Doğrulandı mı?')}): "
                        f"{r.get('Ham Metin (LLM Girdisi)')}")
    for sv in data.rows("Sevkiyatlar"):
        if sv["Sevkiyat No"] in signal.ilgili_sevkiyat:
            satirlar.append(f"- Sevkiyat {sv['Sevkiyat No']}: sapma nedeni={sv.get('Sapma Nedeni')}; "
                            f"not={sv.get('Son Konum / Not')}")
    sonuc = llm.structured(prompts.dis_kosul_prompt("\n".join(satirlar)), DisKosulBileseni,
                           prompts.DIS_KOSUL_SYSTEM)
    if sonuc is None:
        uy.append(Uyari(kod="LLM_HATA", alan="bilesenler.dis_kosul",
                        mesaj="Dış koşul puanı LLM'den alınamadı; girdide kural yok → null (KÇ10)"))
        return DisKosulBileseni()
    gecerli = {r["Sinyal No"] for r in sinyaller} | {signal.sinyal_no}
    kanit = [s for s in sonuc.kanit_sinyaller if s in gecerli]
    if sonuc.puan is None or not sonuc.gerekce or not kanit:
        uy.append(Uyari(kod="KANIT_YETERSIZ", alan="bilesenler.dis_kosul",
                        mesaj="Dış koşul için gerekçe/kanıt yetersiz; puan null"))
        return DisKosulBileseni(puan=None, gerekce=sonuc.gerekce, kanit_sinyaller=kanit)
    return DisKosulBileseni(puan=sonuc.puan, gerekce=sonuc.gerekce, kanit_sinyaller=kanit)


def _aciklama(out_alanlari: dict, uy: list[Uyari]) -> str:
    alanlar = "\n".join(f"{k}: {v}" for k, v in out_alanlari.items())
    metin = llm.text(prompts.aciklama_prompt(alanlar), prompts.ACIKLAMA_SYSTEM)
    if metin:
        return metin
    # Deterministik yedek: yalnızca çıktı alanlarındaki rakamlar.
    o, e, p, k = (out_alanlari.get(x) for x in ("olasilik", "etki", "risk_puani", "risk_kademesi"))
    if p is None:
        return f"Olasılık {o if o is not None else 'hesaplanamadı'}; etki veya bir bileşen eksik, risk puanı üretilmedi."
    return f"Olasılık {o} × Etki {e} = {p} → {k}."


def run(data, signal: SignalOutput, impacts: list[ImpactOutput], run_id: str,
        iliskili_sinyaller: Optional[list[SignalOutput]] = None,
        dis_kosul: Optional[DisKosulBileseni] = None) -> RiskOutput:
    baslangic = _now()
    uy: list[Uyari] = []
    iliskili = iliskili_sinyaller or []

    # 1. Sinyal
    s_puan, s_uyari = scoring.score_signal(data, signal.sinyal_no, signal.sinyal_guvenilirligi)
    if s_uyari:
        uy.append(Uyari(kod="CELISKI", alan="bilesenler.sinyal", mesaj=s_uyari))

    # 2–3. Taraf seçimi + performans + finansal
    taraf, gerekce = scoring.choose_party(signal.ilgili_taraf, signal.olay_tipi)
    perf = PerformansBileseni(taraf=taraf, secim_gerekcesi=gerekce)
    finansal = None
    kaynak = []
    if taraf:
        row, kolon = scoring.find_party(data, taraf)
        if row is None:
            uy.append(Uyari(kod="ESLESME_YOK", alan="bilesenler.performans", mesaj=f"{taraf} karnesi bulunamadı"))
        else:
            perf.kaynak_sutun = kolon
            perf.puan = scoring.score_performance(data, row.get(kolon))
            finansal = scoring.score_financial(data, row.get("Finansal Sağlık Notu"))
            for ad, hesap, hazir in (("performans", perf.puan, row.get("Performans Puanı (1-5)")),
                                     ("finansal", finansal, row.get("Finansal Puan (1-5)"))):
                if hazir is not None and hesap is not None and int(hazir) != hesap:
                    uy.append(Uyari(kod="HAZIR_DEGER_FARKI", alan=f"bilesenler.{ad}",
                                    mesaj=f"Eşikten hesaplanan {hesap} ≠ girdi {hazir}; hesaplanan kullanıldı"))
            kaynak.append(KaynakRef(sayfa="Tasiyicilar" if taraf.startswith("TS") else "Tedarikciler",
                                    anahtarlar=[taraf], sutunlar=[kolon, "Finansal Sağlık Notu"]))
    else:
        uy.append(Uyari(kod="EKSIK_BILESEN", alan="bilesenler.performans", mesaj="Sinyalde ilgili taraf yok"))
    if perf.puan is None or finansal is None:
        uy.append(Uyari(kod="EKSIK_BILESEN", alan="bilesenler", mesaj="Performans/finansal bileşen eksik"))

    # 4. Dış koşul (LLM sınır modeli)
    sinyaller = _context_signals(data, signal, iliskili)
    if dis_kosul is None:
        dis_kosul = _dis_kosul_llm(data, signal, sinyaller, uy)
    elif dis_kosul.puan is not None and not dis_kosul.gerekce:
        uy.append(Uyari(kod="KANIT_YETERSIZ", alan="bilesenler.dis_kosul", mesaj="Dış koşul gerekçesiz verildi"))

    # 5–7. Olasılık, puan, kademe
    olasilik = scoring.compute_probability(data, s_puan, perf.puan, dis_kosul.puan, finansal)
    etkiler = [i.etki_puani for i in impacts or []]
    etki = max(etkiler) if etkiler else None
    if etki is None:
        uy.append(Uyari(kod="EKSIK_BILESEN", alan="etki", mesaj="Impact etki puanı yok; risk puanı üretilmedi (R-K4)"))
    puan = scoring.compute_risk_score(olasilik, etki)
    kademe, aksiyon = scoring.classify_tier(data, puan)

    # 8. Açıklama
    aciklama = _aciklama({"olasilik": olasilik, "etki": etki, "risk_puani": puan, "risk_kademesi": kademe,
                          "sinyal_puani": s_puan, "performans_puani": perf.puan, "taraf": taraf,
                          "dis_kosul_puani": dis_kosul.puan, "dis_kosul_gerekcesi": dis_kosul.gerekce,
                          "finansal_puan": finansal}, uy)

    kaynak += [KaynakRef(sayfa="Parametreler", anahtarlar=["W_Sinyal", "W_Performans", "W_DisKosul",
                                                            "W_Finansal", "EsikYuksek", "EsikOrta"]),
               KaynakRef(sayfa="Esik_Tablolari", anahtarlar=["Performans puanı", "Finansal puan"])]
    return RiskOutput(
        run_id=run_id, senaryo=signal.senaryo, risk_no=signal.risk_no or signal.bagli_risk_no,
        d0=data.d0, what_if_gun=(impacts[0].what_if_gun if impacts else 0),
        baslangic_zamani=baslangic, bitis_zamani=_now(), durum="UYARI" if uy else "TAMAM", uyarilar=uy,
        bilesenler=RiskBilesenleri(sinyal=s_puan, performans=perf, dis_kosul=dis_kosul, finansal=finansal),
        olasilik=olasilik, etki=etki, risk_puani=puan, risk_kademesi=kademe, agent_aksiyonu=aksiyon,
        aciklama=aciklama, kaynak=kaynak)
