"""Gerekçe: LLM (DecisionMetinLLM) + 'gerekçe rakam testi' + deterministik Türkçe şablon yedeği."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Iterable, Optional

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
_SAYI = re.compile(r"\d+(?:[.,]\d+)*")
_CARPAN = {"bin": 1e3, "milyon": 1e6, "milyar": 1e9}


def tl(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


def gun(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def tarih(d) -> str:
    return f"{d.day} {AYLAR[d.month - 1]}"


def _parse(tok: str) -> list[float]:
    """Türkçe (1.234,5) ve İngilizce (1,234.5) yorumlarını birlikte döndürür."""
    out = []
    for s in (tok.replace(".", "").replace(",", "."), tok.replace(",", "")):
        try:
            out.append(float(s))
        except ValueError:
            pass
    return out


def allowed_numbers(values: Iterable, dates: Iterable = ()) -> list[float]:
    nums = [float(v) for v in values if v is not None]
    for d in dates:
        if isinstance(d, (date, datetime)):
            nums += [d.day, d.month, d.year]
    return nums


def number_test(metin: Optional[str], izinli: list[float]) -> bool:
    """Metindeki her rakam tool çıktılarından birine (yuvarlama toleransıyla) karşılık gelmeli."""
    if not metin:
        return True
    for m in _SAYI.finditer(metin):
        sonraki = metin[m.end():m.end() + 8].strip().lower()
        carpan = next((c for k, c in _CARPAN.items() if sonraki.startswith(k)), 1.0)
        adaylar = [x * carpan for x in _parse(m.group())]
        if not any(abs(x - v) <= max(0.51, 0.05 * abs(v)) and (abs(v) > 0 or x == 0)
                   for x in adaylar for v in izinli):
            return False
    return True


def template(ctx: dict) -> tuple[str, str]:
    """(gerekce, olay_ozeti)."""
    if ctx.get("onerilen_ad") is None:
        g = (f"Kısıtları geçen bir strateji bulunamadı. Hiçbir şey yapmamanın maliyeti {tl(ctx['aksiyonsuz'])} TL; "
             f"satınalma ve lojistik ekibinin manuel değerlendirmesi gerekiyor.")
    else:
        g = (f"Stok {tarih(ctx['tukenme'])} tarihinde bitiyor, ana sevkiyat {tarih(ctx['kullanilabilir'])} tarihinde hazır. "
             f"{ctx['onerilen_ad']} ile duruş {gun(ctx['durus'])} gün, toplam maliyet {tl(ctx['toplam'])} TL. "
             f"Hiçbir şey yapmamanın maliyeti {tl(ctx['aksiyonsuz'])} TL; tasarruf {tl(ctx['tasarruf'])} TL.")
    oz = (f"{ctx['sevkiyat_no']} sevkiyatı gecikti; {ctx['malzeme_no']} stoğu {tarih(ctx['tukenme'])} tarihinde bitiyor "
          f"ve aksiyon alınmazsa {gun(ctx['acik'])} gün duruş bekleniyor.")
    return g, oz
