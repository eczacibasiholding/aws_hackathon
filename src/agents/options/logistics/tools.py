"""Logistics tool'ları (04 veri kuralları §3, §5 O3–O6, C6). Deterministik rota matrisi."""
from __future__ import annotations

import math
import re
from typing import Optional

from src.data_access.loader import NexusData


def _varis_uyar(varis: str, tesis: str) -> bool:
    v = str(varis or "")
    return tesis in v or bool(re.search(re.escape(tesis[:4]) + r"(?!-)", v))


def _tokens(s: str) -> list[str]:
    return [t.strip().lower() for t in re.split(r"[/(),]", str(s or "")) if len(t.strip()) >= 3]


def list_routes(data: NexusData, tesis: str, cikis_tesis: Optional[str] = None,
                cikis_lokasyon: Optional[str] = None, mod: Optional[str] = None) -> list[dict]:
    """Hedef tesise giden rotalar. cikis_tesis (transfer) veya cikis_lokasyon (tedarikçi) ile süzülür."""
    out = []
    for r in data.rows("Rota_Secenekleri"):
        kod = r["Rota Kodu"]
        if mod and not kod.startswith(f"R-{mod}-"):
            continue
        if not _varis_uyar(r["Varış"], tesis):
            continue
        cikis = str(r["Çıkış"] or "")
        if cikis_tesis and not cikis.startswith(cikis_tesis):
            continue
        if cikis_lokasyon:
            ilk = cikis.split()[0].lower() if cikis else ""
            if not any(ilk and (ilk in t or t.split()[0] == ilk) for t in _tokens(cikis_lokasyon)):
                continue
        out.append(r)
    return sorted(out, key=lambda r: float(r["Kapı-Kapı Süre (gün)"] or 0))


def brut_kg(data: NexusData, malzeme_no: str, miktar: float) -> float:
    """O5."""
    m = next(r for r in data.rows("Malzemeler") if r["Malzeme No"] == malzeme_no)
    return float(miktar) * float(m["Brüt Ağırlık (kg/birim)"] or 0)


def shipment_count(rota: dict, brut: float) -> int:
    cap = float(rota.get("Sevkiyat Kapasitesi (kg)") or 0)
    return int(math.ceil(round(brut / cap, 9))) if cap > 0 and brut > 0 else 0


def compute_logistics_cost(data: NexusData, rota: dict, brut: float, navlun_dahil: bool = False) -> float:
    """O4."""
    if navlun_dahil:
        return 0.0
    n = shipment_count(rota, brut)
    return (float(rota["Değişken Maliyet (USD/kg)"] or 0) * brut
            + float(rota["Sabit Maliyet (USD/sevkiyat)"] or 0) * n) * float(data.param("USDTRY"))


def compute_co2(rota: dict, brut: float) -> float:
    """O6."""
    return brut / 1000 * float(rota["Mesafe (km)"] or 0) * float(rota["Emisyon Faktörü (kgCO2e/ton-km)"] or 0)


def compute_ready_day(hazirlik: float, kalifikasyon: float, kapi_kapi: float, gumruk: float,
                      kalite: float, what_if: float = 0) -> float:
    """O3 / Formuller #27."""
    return float(hazirlik + kalifikasyon + kapi_kapi + gumruk + kalite + what_if)


def route_risk(data: NexusData, rota: dict, kalifikasyon_gerekli: bool = False) -> int:
    """Formuller #35: Esik_Tablolari 'Rota uygulama riski' (+2 kalifikasyon)."""
    rel = float(rota.get("Zamanında Varış Güvenilirliği") or 0)
    esik = sorted([(float(r["Alt Sınır / Not"]), int(r["Puan (1-5)"])) for r in data.rows("Esik_Tablolari")
                   if r["Tablo"] == "Rota uygulama riski"], reverse=True)
    puan = next((p for a, p in esik if rel >= a), 5) if esik else int(rota.get("Uygulama Riski (1-5)") or 3)
    return min(5, puan + (2 if kalifikasyon_gerekli else 0))


def capacity_ok(rota: dict, brut: float) -> bool:
    """C6 — sevkiyat sayısıyla (O4) kapasite her zaman karşılanır; kapasite tanımsızsa KALDI."""
    return float(rota.get("Sevkiyat Kapasitesi (kg)") or 0) > 0
