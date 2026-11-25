"""Orkestratör — deterministik durum makinesi, LLM çağırmaz (K5, O1–O8, SCOPE §4.1).

BEKLE → SINYAL → {AYIKLA→KAPAT | eşleşme yok→IZLEME | ANALIZ→ETKI∥RISK→ kademe kapısı}
Yüksek → SECENEK → KARAR → ONAY_BEKLIYOR · Orta → SECENEK (hazırda) → UYARI · Düşük → IZLEME
Hata → HATA (kısmi sonuç "tamamlanamadı"). WHAT_IF yok (D7).
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from src.contracts.schemas import InsanKarari, KararKaydi
from src.data_access.loader import load_cached
from src.orchestrator.store import Store

log = logging.getLogger("nexus.orchestrator")

try:  # AgentCore Observability: OpenTelemetry span'leri (ADOT ile dışa aktarılır)
    from opentelemetry import trace

    _tracer = trace.get_tracer("nexus.orchestrator")
except Exception:  # pragma: no cover
    _tracer = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def _span(ad: str, **attrs):
    t = time.time()
    if _tracer:
        with _tracer.start_as_current_span(ad) as sp:
            for k, v in attrs.items():
                sp.set_attribute(k, str(v))
            yield sp
    else:
        yield None
    log.info("adım=%s süre=%.2fs %s", ad, time.time() - t, attrs)


def _dump(m) -> Any:
    if isinstance(m, list):
        return [_dump(x) for x in m]
    return m.model_dump(mode="json") if hasattr(m, "model_dump") else m


def _data():
    d = load_cached(os.environ.get("NEXUS_INPUT_URI"))
    st = Store()
    d.extra_signals = [st.get(k) for k in st.list("signals/") if k.endswith(".json")]
    return d, st


# ---------- risk kayıt defteri (D8) ----------
def _risk_no(st: Store, sevkiyat: str, malzeme: str, sinyal_no: str, run_id: str) -> str:
    reg = st.get("registry/risks.json", {"riskler": {}})
    anahtar = f"{sevkiyat}|{malzeme}"
    r = reg["riskler"].get(anahtar)
    if not r:
        r = {"risk_no": f"R-{len(reg['riskler']) + 1:02d}", "sinyaller": [], "son_run_id": None}
        reg["riskler"][anahtar] = r
    if sinyal_no not in r["sinyaller"]:
        r["sinyaller"].append(sinyal_no)
    r["son_run_id"] = run_id
    st.put("registry/risks.json", reg)
    return r["risk_no"]


def _yeni_olay_no(st: Store) -> str:
    mevcut = [int(k.split("NXS-26-")[1].split(".")[0]) for k in st.list("decisions/") if "NXS-26-" in k]
    return f"NXS-26-{max([24] + mevcut) + 1:03d}"  # D9: NXS-26-025'ten başlar


def sinyal_isle(payload: dict) -> dict:
    from src.agents.decision import agent as decision
    from src.agents.impact import agent as impact
    from src.agents.options import agent as options
    from src.agents.risk import agent as risk
    from src.agents.signal import agent as signal

    sinyal_no = payload["sinyal_no"]
    run_id = payload.get("run_id") or f"run-{_now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"
    data, st = _data()
    ozet: dict[str, Any] = {"run_id": run_id, "sinyal_no": sinyal_no, "kaynak": payload.get("kaynak", "MANUEL"),
                            "baslangic": _now().isoformat(), "durumlar": ["BEKLE", "SINYAL"]}

    def bitir(durum: str, **ek):
        ozet.update(durum=durum, bitis=_now().isoformat(), **ek)
        # UI/API düz alanları (ui/app.js, src/api/handler.py)
        sg, rk = ozet.get("signal") or {}, ozet.get("risk") or {}
        ozet.update(baslangic_zamani=ozet["baslangic"], bitis_zamani=ozet["bitis"],
                    sevkiyat_no=(sg.get("sevkiyat") or [None])[0], malzeme_no=(sg.get("malzeme") or [None])[0],
                    risk_puani=rk.get("puan"), risk_kademesi=rk.get("kademe"), olasilik=rk.get("olasilik"),
                    etki=rk.get("etki"), karar="Onay Bekliyor" if durum == "ONAY_BEKLIYOR" else None)
        ozet["durumlar"].append(durum)
        st.put(f"runs/{run_id}/summary.json", ozet)
        return ozet

    try:
        with _span("signal", sinyal_no=sinyal_no, run_id=run_id):
            sig = signal.run(data, sinyal_no, run_id)
        st.put(f"runs/{run_id}/signal.json", _dump(sig))
        ozet["signal"] = {"isleme_karari": sig.isleme_karari, "sevkiyat": sig.ilgili_sevkiyat,
                          "malzeme": sig.ilgili_malzeme, "gecikme_gun": sig.tahmini_gecikme_gun}
        if sig.isleme_karari == "AYIKLA":
            return bitir("KAPAT", gerekce=sig.ayiklama_nedeni)
        if not sig.ilgili_sevkiyat or not sig.ilgili_malzeme:
            return bitir("IZLEME", uyari="Sinyal bir sevkiyat/malzemeye eşleşmedi")

        risk_no = _risk_no(st, sig.ilgili_sevkiyat[0], sig.ilgili_malzeme[0], sinyal_no, run_id)
        ozet["risk_no"] = risk_no
        sig = sig.model_copy(update={"risk_no": risk_no, "bagli_risk_no": risk_no})
        st.put(f"runs/{run_id}/signal.json", _dump(sig))

        ozet["durumlar"].append("ANALIZ")
        with _span("impact", run_id=run_id, risk_no=risk_no):
            imps = impact.run(data, sig, run_id)
        imps = [i.model_copy(update={"risk_no": risk_no}) for i in imps]
        st.put(f"runs/{run_id}/impact.json", _dump(imps))
        if not imps:
            return bitir("IZLEME", uyari="Etki hesaplanamadı (eşleşen stok/hat yok)")

        with _span("risk", run_id=run_id, risk_no=risk_no):
            rsk = risk.run(data, sig, imps, run_id)
        rsk = rsk.model_copy(update={"risk_no": risk_no})
        st.put(f"runs/{run_id}/risk.json", _dump(rsk))
        kademe = rsk.risk_kademesi
        ozet.update(risk={"olasilik": rsk.olasilik, "etki": rsk.etki, "puan": rsk.risk_puani, "kademe": kademe})
        ozet["durumlar"].append(f"RISK_KADEME:{kademe}")
        if kademe not in ("Yüksek", "Orta"):
            return bitir("IZLEME")

        imp = max(imps, key=lambda i: i.aksiyonsuz_maliyet_try)
        with _span("options", run_id=run_id):
            opt = options.run(data, sig, imp, rsk, run_id)
        opt = opt.model_copy(update={"risk_no": risk_no})
        st.put(f"runs/{run_id}/options.json", _dump(opt))
        if kademe == "Orta":
            return bitir("UYARI", not_="Seçenekler hazırda tutuluyor (O3)")

        with _span("decision", run_id=run_id):
            dec = decision.run(data, sig, imp, rsk, opt, run_id)
        dec = dec.model_copy(update={"risk_no": risk_no})
        olay_no = _yeni_olay_no(st)
        dec = dec.model_copy(update={"karar_kaydi_taslagi": dec.karar_kaydi_taslagi.model_copy(update={"olay_no": olay_no})})
        st.put(f"runs/{run_id}/decision.json", _dump(dec))

        kayit = _karar_kaydi(data, st, olay_no, risk_no, sig, imp, opt, dec)
        st.put(f"decisions/{olay_no}.json", _dump(kayit))
        ozet.update(olay_no=olay_no, oneri=dec.oneri_karti.onerilen_strateji_kodu)
        return bitir("ONAY_BEKLIYOR")
    except Exception as e:  # O2: sözleşme/Bedrock/zaman aşımı → HATA
        log.exception("akış hatası")
        return bitir("HATA", hata=f"{type(e).__name__}: {e}", not_="tamamlanamadı")


def _sinyal_satiri(data, sinyal_no: str) -> dict:
    for r in data.rows("Risk_Sinyalleri") + list(data.extra_signals or []):
        if r and r.get("Sinyal No") == sinyal_no:
            return r
    return {}


def _zaman(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        t = datetime.fromisoformat(str(v))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _karar_kaydi(data, st, olay_no, risk_no, sig, imp, opt, dec) -> KararKaydi:
    satir = _sinyal_satiri(data, sig.sinyal_no)
    yayin, tespit = _zaman(satir.get("Yayın Zamanı")), _zaman(satir.get("Tespit Zamanı")) or sig.baslangic_zamani
    kart = dec.oneri_karti
    secili = next((s for s in opt.stratejiler if s.strateji_kodu == kart.onerilen_strateji_kodu), None)
    sim = next((k for k in dec.karsilastirma if k.strateji_kodu == kart.onerilen_strateji_kodu), None)
    onerilen_maliyet = getattr(sim, "toplam_maliyet_try", None)
    onerilen_durus = getattr(sim, "durus_gun", None)
    oneri_z = dec.bitis_zamani
    return KararKaydi(
        olay_no=olay_no, risk_no=risk_no, sinyal_nolari=[sig.sinyal_no],
        sinyal_tespit_zamani=tespit, oneri_zamani=oneri_z, karar="Onay Bekliyor",
        onerilen_strateji_kodu=kart.onerilen_strateji_kodu,
        aksiyonsuz_maliyet_try=imp.aksiyonsuz_maliyet_try,
        onerilen_maliyet_try=onerilen_maliyet,
        tasarruf_try=dec.karar_kaydi_taslagi.tasarruf_try,
        tespit_suresi_dk=max(0.0, (tespit - yayin).total_seconds() / 60) if yayin else None,
        oneri_suresi_dk=max(0.0, (oneri_z - tespit).total_seconds() / 60),
        tarih=data.d0, kurulus_kodu=_kurulus(data, imp.malzeme_no),
        olay_tipi=kart.olay_tipi or _olay_tipi(secili),
        olay_ozeti=kart.olay_ozeti,
        sinyal_yayin_zamani=yayin, onerilen_aksiyon=secili.strateji_adi if secili else None,
        risk_gerceklesmeden_aksiyon=oneri_z < imp.tukenme_tarihi.replace(tzinfo=imp.tukenme_tarihi.tzinfo or timezone.utc),
        onlenen_durus_gun=(imp.acik_durus_gun - onerilen_durus) if onerilen_durus is not None else None,
        kullanici_geri_bildirimi="Yetkili onayı bekleniyor.",
    )


def _olay_tipi(strateji):
    """LLM sınıflandırması yoksa deterministik yedek: önerilen stratejinin bileşen tiplerinden."""
    if not strateji or not strateji.bilesenler:
        return None
    tipler = {b.tip for b in strateji.bilesenler}
    tedarik = bool(tipler & {"TRANSFER", "ALTERNATIF_TEDARIK_ROTA"})
    lojistik = bool(tipler & {"ROTA_DEGISIKLIGI", "ALTERNATIF_TEDARIK_ROTA"})
    return "Birleşik (Tedarik + Lojistik)" if tedarik and lojistik else "Tedarik" if tedarik else "Lojistik"


def _kurulus(data, malzeme_no: str):
    for r in data.rows("Malzemeler"):
        if r.get("Malzeme No") == malzeme_no:
            return r.get("Kuruluş Kodu")
    return None


def insan_karari(payload: dict) -> dict:
    """O4: kararı yalnızca orkestratör yazar."""
    st = Store()
    ik = InsanKarari(olay_no=payload["olay_no"], karar=payload["karar"],
                     onaylayan_rol=payload.get("onaylayan_rol", "Satınalmacı"),
                     karar_zamani=_zaman(payload.get("karar_zamani")) or _now(),
                     revize_notu=payload.get("revize_notu"), yanlis_alarm=bool(payload.get("yanlis_alarm")))
    eski = st.get(f"decisions/{ik.olay_no}.json")
    if not eski:
        return {"durum": "HATA", "hata": f"{ik.olay_no} bulunamadı"}
    k = KararKaydi.model_validate(eski)
    k = k.model_copy(update=dict(
        karar=ik.karar, karar_zamani=ik.karar_zamani, onaylayan_rol=ik.onaylayan_rol,
        revize_notu=ik.revize_notu, yanlis_alarm_mi=ik.karar == "Reddedildi" and ik.yanlis_alarm,
        onay_suresi_dk=max(0.0, (ik.karar_zamani - k.oneri_zamani).total_seconds() / 60),
        kullanici_geri_bildirimi=ik.revize_notu or payload.get("not") or ik.karar))
    KararKaydi.model_validate(k.model_dump())
    st.put(f"decisions/{ik.olay_no}.json", _dump(k))
    return {"durum": "KAYIT", "karar_kaydi": _dump(k)}


def toplu_tarama(payload: dict) -> dict:
    """D17: canlı demo sinyalleri hariç tümünü işler."""
    from src.agents.signal import agent as signal

    data, _ = _data()
    h = payload.get("haric") or os.environ.get("DEMO_CANLI_SINYALLER", "")
    haric = set(filter(None, h.split(",") if isinstance(h, str) else h))
    secili = payload.get("sinyaller") or [s for s in signal.list_signals(data) if s not in haric]
    return {"durum": "TAMAM", "sonuclar": [sinyal_isle({"sinyal_no": s, "kaynak": "TOPLU"}) for s in secili]}
