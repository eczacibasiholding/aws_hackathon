"""H1/H2: günlük kova simülasyonu (gün başı giriş, gün içi tüketim, kısmi duruş kesirli)."""
from __future__ import annotations

import math

from src.contracts.schemas import SimulasyonGunu, Strateji, StratejiSimulasyonu

UFUK = 60


def inflows(strateji: Strateji, ana_gun: float, ana_miktar: float) -> tuple[dict[int, float], float]:
    """Gün → giriş; ve değerlendirme ufku (ana sevkiyatın etkin günü)."""
    g: dict[int, float] = {}
    ufuk = ana_gun
    ana_eklendi = False
    for b in strateji.bilesenler:
        gun = int(math.ceil(b.hazir_gun - 1e-9))
        if b.tip == "ROTA_DEGISIKLIGI":
            ufuk = b.hazir_gun
            ana_eklendi = True
        g[gun] = g.get(gun, 0.0) + b.miktar
    if not ana_eklendi:
        gun = int(math.ceil(ana_gun - 1e-9))
        g[gun] = g.get(gun, 0.0) + ana_miktar
    return g, ufuk


def simulate_inventory(strateji: Strateji, stok0: float, gunluk: float, ana_gun: float, ana_miktar: float
                       ) -> tuple[StratejiSimulasyonu, float]:
    giris, ufuk = inflows(strateji, ana_gun, ana_miktar)
    gunler, stok, durus = [], float(stok0), 0.0
    for t in range(UFUK + 1):
        gir = giris.get(t, 0.0)
        mevcut = stok + gir
        oran = max(0.0, gunluk - mevcut) / gunluk if gunluk > 0 else 0.0
        stok = max(0.0, mevcut - gunluk)
        if t < ufuk:
            durus += oran
        gunler.append(SimulasyonGunu(gun=t, giris=gir, gun_sonu_stok=round(stok, 6), durus_orani=round(oran, 9)))
    return StratejiSimulasyonu(strateji_kodu=strateji.strateji_kodu, gunler=gunler), durus
