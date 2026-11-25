"""Sourcing tool'ları (04 veri kuralları §2, §5 O1/O2/O7/O8/O9, C1–C5). Deterministik."""
from __future__ import annotations

import math
from typing import Optional

from src.data_access.loader import NexusData

# Formuller #37: hibrit/kısmi miktar 25'in katına yukarı yuvarlanır (ambalaj/varil katı).
AMBALAJ_KATI = 25


def _row(data: NexusData, sheet: str, key: str, val) -> Optional[dict]:
    return next((r for r in data.rows(sheet) if r.get(key) == val), None)


def material(data: NexusData, malzeme_no: str) -> dict:
    return _row(data, "Malzemeler", "Malzeme No", malzeme_no) or {}


def find_transfer_sources(data: NexusData, malzeme_no: str, hedef_tesis: str) -> list[dict]:
    """Aynı malzeme, farklı tesis, Transfer Edilebilir Miktar > 0. Formül #9 tutarlılığı da hesaplanır."""
    koruma = float(data.param("KorumaUfku"))
    out = []
    for r in data.rows("Stok_Durumu"):
        if r["Malzeme No"] != malzeme_no or r["Tesis Kodu"] == hedef_tesis:
            continue
        miktar = float(r.get("Transfer Edilebilir Miktar") or 0)
        formul = max(0.0, float(r["Serbest Stok"] or 0) - float(r.get("Min. Rezerv (servis/ruhsat)") or 0)
                     - float(r.get("Emniyet Stoğu Miktarı") or 0) - float(r.get("Günlük Tüketim") or 0) * koruma)
        if miktar > 0:
            out.append({"stok_anahtari": r["Stok Anahtarı"], "tesis": r["Tesis Kodu"], "miktar": miktar,
                        "formul_tutarli": abs(formul - miktar) < 0.5})
    return sorted(out, key=lambda x: -x["miktar"])


def usd_price(data: NexusData, fiyat: float, para: str) -> float:
    """O1."""
    if para == "USD":
        return float(fiyat)
    if para == "EUR":
        return float(fiyat) * float(data.param("EURUSD"))
    return float(fiyat) / float(data.param("USDTRY"))


def compute_landed_cost(data: NexusData, kaynak: dict) -> float:
    """O2: USD fiyat + (navlun dahil değilse) standart navlun."""
    usd = usd_price(data, kaynak["Birim Fiyat"], kaynak["Para Birimi"])
    nav = 0.0 if kaynak.get("Navlun Fiyata Dahil mi?") == "Evet" else float(kaynak.get("Standart Navlun+Liman (USD/birim)") or 0)
    return usd + nav


def list_alt_suppliers(data: NexusData, malzeme_no: str) -> list[dict]:
    return [r for r in data.rows("Tedarik_Kaynaklari")
            if r["Malzeme No"] == malzeme_no and r.get("Ana Kaynak mı?") != "Evet"]


def main_supplier_landed(data: NexusData, malzeme_no: str) -> Optional[float]:
    ana = material(data, malzeme_no).get("Ana Tedarikçi")
    r = _row(data, "Tedarik_Kaynaklari", "Kaynak Anahtarı", f"{malzeme_no}|{ana}")
    return compute_landed_cost(data, r) if r else None


def check_qualification(data: NexusData, kaynak: dict) -> dict:
    """C4 (kalifikasyon gerekli → elenir) ve C5 (SAGLIK → yalnızca ruhsatta kayıtlı)."""
    mat = material(data, kaynak["Malzeme No"])
    durum = str(kaynak.get("Kalifikasyon Durumu") or "")
    kalif_gun = float(kaynak.get("Kalifikasyon Süresi (gün)") or 0)
    if "Kalifikasyon Gerekli" in durum:
        return {"gecti": False, "kisit": "C4", "kalif_gun": kalif_gun,
                "neden": f"Kalifikasyon Gerekli – {kalif_gun:g} günlük kalifikasyon süresi ufuk dışında"}
    if mat.get("Kuruluş Kodu") == "SAGLIK" and "Ruhsatta Kayıtlı" not in durum:
        return {"gecti": False, "kisit": "C5", "kalif_gun": kalif_gun,
                "neden": "İlaç malzemesi: kaynak ruhsatta kayıtlı değil (GMP/özel koşul)"}
    return {"gecti": True, "kisit": None, "kalif_gun": 0.0, "neden": None}


def price_diff_usd(data: NexusData, kaynak: dict) -> float:
    """Formuller #31: alternatif USD fiyat − ana tedarikçi iniş maliyeti."""
    ana = main_supplier_landed(data, kaynak["Malzeme No"])
    if ana is None:
        return 0.0
    return usd_price(data, kaynak["Birim Fiyat"], kaynak["Para Birimi"]) - ana


def extra_material_cost_try(data: NexusData, kaynak: dict, miktar: float) -> float:
    """O8 / Formuller #32."""
    return price_diff_usd(data, kaynak) * miktar * float(data.param("USDTRY"))


def test_cost_try(data: NexusData, malzeme_no: str) -> float:
    """O9: kuruluşa göre test/muayene maliyeti."""
    k = material(data, malzeme_no).get("Kuruluş Kodu")
    return float({"SAGLIK": data.param("QCTestMaliyeti"), "KARO": data.param("KilLabTestGunluk"),
                  "BANYO": data.param("ElektronikMuayeneMaliyeti")}.get(k, 0) or 0)


def compute_hybrid_qty(hedef_gun: float, tampon: float, gunluk: float, stok: float,
                       transfer: float, moq: float) -> float:
    """O7 / Formuller #37."""
    ham = max(0.0, (hedef_gun + tampon) * gunluk - stok - transfer)
    yuv = math.ceil(round(ham / AMBALAJ_KATI, 9)) * AMBALAJ_KATI
    return float(max(moq, yuv))


def check_supply_constraints(kaynak: dict, miktar: float, sure_gun: float) -> list[str]:
    """C2, C3 — kalan (KALDI) kısıtları döndürür."""
    kalan = []
    if miktar < float(kaynak.get("Spot MOQ (birim)") or 0):
        kalan.append("C2")
    ust = float(kaynak.get("Hazır Stok (birim)") or 0) + float(kaynak.get("Ek Üretim Kapasitesi (birim/gün)") or 0) * max(0.0, sure_gun)
    if miktar > ust + 1e-6:
        kalan.append("C3")
    return kalan
