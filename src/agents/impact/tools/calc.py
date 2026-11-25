"""Impact deterministik hesap tool'ları (03_impact_agent_veri_kurallari.md §3–§4, I1–I13).

LLM hiçbir sayıyı üretmez (I-K1). Tüm eşikler/parametreler girdiden okunur.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

import pandas as pd


def _to_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    return pd.Timestamp(v).date()


def _num(v: Any, default: float = 0.0) -> float:
    return default if v is None else float(v)


# ---------- Kayıt bulma ----------
def resolve_chain(data, sevkiyat_no: str) -> dict:
    """Sevkiyat → stok → hat(lar) → müşteri siparişleri zincirini kurar (veri md §3)."""
    sv = next((r for r in data.rows("Sevkiyatlar") if r["Sevkiyat No"] == sevkiyat_no), None)
    if sv is None:
        return {"sevkiyat": None}
    mat, tesis = sv["Malzeme No"], sv["Nihai Varış Tesisi"]
    anahtar = f"{tesis}|{mat}"
    stok = next((r for r in data.rows("Stok_Durumu") if r["Stok Anahtarı"] == anahtar), None)
    malzeme = next((r for r in data.rows("Malzemeler") if r["Malzeme No"] == mat), None)
    hatlar = [r for r in data.rows("Uretim_Hatlari")
              if r["Kritik Malzeme No"] == mat and r["Tesis Kodu"] == tesis]
    po = next((r for r in data.rows("Acik_Siparisler") if str(r.get("PO No")) == str(sv.get("PO No"))), None)
    return {"sevkiyat": sv, "stok": stok, "stok_anahtari": anahtar, "malzeme": malzeme,
            "hatlar": hatlar, "po": po}


def orders_for_line(data, hat_kodu: str) -> list[dict]:
    return [r for r in data.rows("Musteri_Siparisleri") if r["Hat Kodu"] == hat_kodu]


# ---------- I1–I6 ----------
def compute_daily_need(hat: dict) -> float:
    """I1: Planlı Günlük Üretim × Mamul Başına Malzeme × (1 + Fire Oranı)."""
    return (_num(hat["Planlı Günlük Üretim (mamul)"]) * _num(hat["Mamul Başına Malzeme"])
            * (1 + _num(hat["Fire Oranı"])))


def compute_coverage(serbest_stok: float, gunluk_tuketim: float) -> Optional[float]:
    """I2: Serbest Stok ÷ Günlük Tüketim (yalnızca serbest stok, I-K2)."""
    if not gunluk_tuketim:
        return None
    return serbest_stok / gunluk_tuketim


def compute_depletion(d0: date, kapsama_gun: float) -> datetime:
    """I3: D0 + kapsama (kesirli gün → saat dahil)."""
    return datetime.combine(d0, datetime.min.time()) + timedelta(days=kapsama_gun)


def compute_usable_date(sv: dict, base_col: str, what_if_gun: float = 0) -> date:
    """I4/I5: varış + gümrük + iç nakliye + kalite (+ WhatIfGun). Limana varış tek başına kullanılmaz (I-K3)."""
    gun = (_num(sv.get("Gümrük (gün)")) + _num(sv.get("İç Nakliye (gün)"))
           + _num(sv.get("Kalite Serbest Bırakma (gün)")) + what_if_gun)
    return _to_date(sv[base_col]) + timedelta(days=gun)


def day_index(d0: date, d: date) -> float:
    """I6: (tarih − D0).days."""
    return float((d - d0).days)


# ---------- I7–I12 ----------
def compute_gap(kullanilabilir_gun: float, kapsama_gun: float) -> float:
    """I7: max(0, kullanılabilir gün − kapsama)."""
    return max(0.0, kullanilabilir_gun - kapsama_gun)


def compute_daily_downtime_cost(hat: dict) -> float:
    """I8: üretim × katkı payı × (1 − telafi oranı) + boşta sabit maliyet."""
    return (_num(hat["Planlı Günlük Üretim (mamul)"]) * _num(hat["Birim Katkı Payı (TRY)"])
            * (1 - _num(hat["Telafi Edilebilir Üretim Oranı"]))
            + _num(hat["Duruşta Günlük Sabit Maliyet (TRY)"]))


def compute_downtime_cost(acik_gun: float, gunluk_maliyet: float, yeniden_baslatma: float) -> float:
    """I9: açık × günlük duruş maliyeti + (açık > 0 ise bir kez) yeniden başlatma (I-K5)."""
    if acik_gun <= 0:
        return 0.0
    return acik_gun * gunluk_maliyet + yeniden_baslatma


def find_orders_at_risk(orders: list[dict], tukenme: datetime, kullanilabilir: date) -> list[dict]:
    """I10: Gerekli Üretim Tarihi stok bitişi ile malzeme gelişi arasına düşüyorsa (tükenme < t ≤ geliş)."""
    out = []
    for o in orders:
        g = _to_date(o.get("Gerekli Üretim Tarihi"))
        if g is None:
            continue
        if datetime.combine(g, datetime.min.time()) > tukenme and g <= kullanilabilir:
            out.append(o)
    return out


def compute_penalty(order: dict, kullanilabilir: date) -> tuple[float, float]:
    """I11: gecikme günü = max(0, kullanılabilir tarih − gerekli üretim tarihi); ceza = gecikme × günlük ceza."""
    g = _to_date(order["Gerekli Üretim Tarihi"])
    gecikme = float(max(0, (kullanilabilir - g).days))
    return gecikme, gecikme * _num(order.get("Gecikme Cezası (TRY/gün)"))


def compute_impact_score(acik_gun: float, aksiyonsuz: float, esik_yuksek: float, esik_orta: float,
                         tampon_gun: float, emniyet_gun: Optional[float]) -> int:
    """I13: açık varsa maliyet eşikleri (5/4/3); yoksa tampon < emniyet stoğu → 2, aksi → 1."""
    if acik_gun > 0:
        if aksiyonsuz >= esik_yuksek:
            return 5
        if aksiyonsuz >= esik_orta:
            return 4
        return 3
    if emniyet_gun is not None and tampon_gun < emniyet_gun:
        return 2
    return 1
