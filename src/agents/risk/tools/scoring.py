"""Risk deterministik puanlama tool'ları (02_risk_agent_veri_kurallari.md §3).
Eşik/ağırlıklar Esik_Tablolari ve Parametreler'den okunur (R-K3)."""
from __future__ import annotations

from typing import Optional

LOJISTIK_IPUCLARI = ("liman", "gemi", "aktarma", "lojistik", "navlun", "rıhtım", "taşıyıcı", "kargo",
                     "port", "vessel", "feeder", "sefer", "konteyner", "kızıldeniz")


def find_party(data, taraf: str) -> tuple[Optional[dict], Optional[str]]:
    """TSxx → Tasiyicilar (Zamanında Varış Oranı), TD5xxx → Tedarikciler (OTIF Oranı)."""
    if taraf.startswith("TS"):
        r = next((r for r in data.rows("Tasiyicilar") if r["Taşıyıcı No"] == taraf), None)
        return r, "Zamanında Varış Oranı"
    r = next((r for r in data.rows("Tedarikciler") if r["Tedarikçi No"] == taraf), None)
    return r, "OTIF Oranı"


def choose_party(taraflar: list[str], olay_tipi: Optional[str]) -> tuple[Optional[str], str]:
    """Deterministik taraf seçimi (LLM yedeği): tek tip varsa o; ikisi varsa olay tipi lojistikse taşıyıcı."""
    ts = [t for t in taraflar if t.startswith("TS")]
    td = [t for t in taraflar if t.startswith("TD")]
    if ts and not td:
        return ts[0], "Sinyaldeki tek taraf taşıyıcı."
    if td and not ts:
        return td[0], "Sinyaldeki tek taraf tedarikçi."
    if not ts and not td:
        return None, "Sinyalde taraf yok."
    lojistik = any(k in (olay_tipi or "").lower() for k in LOJISTIK_IPUCLARI)
    if lojistik:
        return ts[0], f"Olay tipi lojistik ('{olay_tipi}') → taşıyıcı karnesi."
    return td[0], f"Olay tipi tedarik kaynaklı ('{olay_tipi}') → tedarikçi karnesi."


def _esik(data, tablo: str) -> list[dict]:
    return [r for r in data.rows("Esik_Tablolari") if r["Tablo"] == tablo]


def score_performance(data, oran: Optional[float]) -> Optional[int]:
    """Oran ≥ alt sınır → puan (yüksekten düşüğe ilk eşleşen). 1 iyi, 5 kötü."""
    if oran is None:
        return None
    for r in sorted(_esik(data, "Performans puanı"), key=lambda r: -float(r["Alt Sınır / Not"])):
        if float(oran) >= float(r["Alt Sınır / Not"]):
            return int(r["Puan (1-5)"])
    return None


def score_financial(data, not_: Optional[str]) -> Optional[int]:
    if not not_:
        return None
    for r in _esik(data, "Finansal puan"):
        if str(r["Alt Sınır / Not"]).strip().upper() == str(not_).strip().upper():
            return int(r["Puan (1-5)"])
    return None


def score_signal(data, sinyal_no: str, guvenilirlik: int) -> tuple[int, Optional[str]]:
    """Sinyal güvenilirliğini Risk_Kaynaklari tabanıyla kıyaslar (taban ≤ puan ≤ taban+1)."""
    sg = next((r for r in data.rows("Risk_Sinyalleri") if r["Sinyal No"] == sinyal_no), None)
    if sg is None:
        return guvenilirlik, None
    kaynak = next((r for r in data.rows("Risk_Kaynaklari") if r["Kaynak Kodu"] == sg.get("Kaynak Kodu")), None)
    if kaynak is None:
        return guvenilirlik, None
    taban = int(kaynak["Taban Güvenilirlik (1-5)"])
    if not (taban <= guvenilirlik <= min(5, taban + 1)):
        return guvenilirlik, f"Sinyal güvenilirliği {guvenilirlik}, kaynak tabanı {taban} ile tutarsız"
    return guvenilirlik, None


def compute_probability(data, sinyal: Optional[float], performans: Optional[float],
                        dis_kosul: Optional[float], finansal: Optional[float]) -> Optional[float]:
    """W_Sinyal×s + W_Performans×p + W_DisKosul×d + W_Finansal×f; eksik bileşende None (sıfır kabul edilmez)."""
    if None in (sinyal, performans, dis_kosul, finansal):
        return None
    w = [float(data.param(k)) for k in ("W_Sinyal", "W_Performans", "W_DisKosul", "W_Finansal")]
    return round(w[0] * sinyal + w[1] * performans + w[2] * dis_kosul + w[3] * finansal, 6)


def compute_risk_score(olasilik: Optional[float], etki: Optional[int]) -> Optional[float]:
    if olasilik is None or etki is None:
        return None
    return round(olasilik * etki, 6)


AKSIYON = {"Yüksek": "Tam analiz + onaya sun", "Orta": "Uyarı + seçenek hazırda", "Düşük": "İzle"}


def classify_tier(data, puan: Optional[float]) -> tuple[Optional[str], Optional[str]]:
    if puan is None:
        return None, None
    if puan >= float(data.param("EsikYuksek")):
        k = "Yüksek"
    elif puan >= float(data.param("EsikOrta")):
        k = "Orta"
    else:
        k = "Düşük"
    return k, AKSIYON[k]
