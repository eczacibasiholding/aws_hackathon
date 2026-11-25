"""LLM kapalı/başarısızken deterministik çıkarım yedeği (regex/anahtar kelime) → SignalLLMCikarimi."""
from __future__ import annotations

import re
from datetime import date, datetime

from src.contracts.schemas import SignalLLMCikarimi

_AYLAR = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_NEG = re.compile(r"not affected|unaffected|etkilenmed|etkilenmiyor", re.I)

TAKIP_RE = re.compile(r"\b[A-Z]{3}-[A-Z]{3}-\d{2}-\d{4}\b")
PO_RE = re.compile(r"\b45\d{8}\b")
GEMI_RE = re.compile(r"\bMV\s+((?:[A-Z][A-Z0-9]+\s?){1,4})")


def cumleler(metin: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<=[.!?])\s+", metin) if c.strip()]


def _tarihler(s: str, yil: int) -> list[date]:
    out = []
    for g, a, y in re.findall(r"\b(\d{1,2})[-\s]([A-Za-z]{3})(?:[-\s](\d{4}))?", s):
        if a.lower() in _AYLAR:
            out.append(date(int(y or yil), _AYLAR[a.lower()], int(g)))
    for g, a, y in re.findall(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", s):
        out.append(date(int(y), int(a), int(g)))
    return out


def gecikme_cikar(metin: str, yil: int) -> float | None:
    m = re.search(r"delay of (\d+(?:[.,]\d+)?) days?|by (\d+) days?|(\d+) güne? (?:kadar )?(?:gecikme|kesinti)?", metin, re.I)
    if m and (m.group(1) or m.group(2)):
        return float((m.group(1) or m.group(2)).replace(",", "."))
    for c in cumleler(metin):
        t = _tarihler(c, yil)
        if len(t) >= 2:
            low = c.lower()
            if "previous" in low or "instead of" in low:  # yeni ... (önceki/instead of eski)
                return float((t[0] - t[1]).days)
            return float((t[1] - t[0]).days)  # from A to B / A → B
    return None


def alternatif_cikar(metin: str) -> str | None:
    m = re.search(r"discharge at ([A-Z][\w]+)", metin)
    if m:
        return f"{m.group(1)} varış limanı değişikliği (COD) mümkün"
    m = re.search(r"loading via ([A-Z][\w]+)(?: \(([^)]+)\))?.*?approx\.?\s*([\d,.]+\s*MT)?", metin)
    if m:
        miktar = f" {m.group(3)}" if m.group(3) else ""
        return f"{m.group(1)} üzerinden{miktar} kısmi yükleme"
    m = re.search(r"hold ([\d,.]+ \w+) .*? at our ([A-Z][\w ]+?) (?:3PL )?warehouse", metin)
    if m:
        return f"{m.group(2)} deposunda {m.group(1)} hazır stok"
    return None


def deterministik_cikarim(metin: str, taraf_adlari: list[str], yil: int) -> SignalLLMCikarimi:
    takip, alintilar = [], {}
    for c in cumleler(metin):
        for t in TAKIP_RE.findall(c):
            if not _NEG.search(c) and t not in takip:
                takip.append(t)
                alintilar.setdefault("takip_no_ipuclari", c)
    po = list(dict.fromkeys(PO_RE.findall(metin)))
    gemiler = list(dict.fromkeys(g.strip() for g in GEMI_RE.findall(metin)))
    norm = metin.lower()
    taraflar = [ad for ad in taraf_adlari if ad and ad.lower().split()[0] in norm and len(ad.split()[0]) > 3]
    return SignalLLMCikarimi(
        taraf_adlari=taraflar, takip_no_ipuclari=takip, po_ipuclari=po,
        gemi_adlari=[f"MV {g}" for g in gemiler],
        tahmini_gecikme_gun=gecikme_cikar(metin, yil),
        alternatif_ipucu=alternatif_cikar(metin), alintilar=alintilar,
    )
