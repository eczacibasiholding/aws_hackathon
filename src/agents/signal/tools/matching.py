"""Deterministik eşleştirme, güvenilirlik, gürültü filtresi, gruplama (01 veri kuralları §3-§4)."""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from src.contracts.schemas import SignalLLMCikarimi

AYIKLA_DURUM = {"Yanlış Alarm", "Kapatıldı", "Bilgi"}


def _n(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def eslestir(data, c: SignalLLMCikarimi) -> tuple[list[str], list[str], list[str], list[str]]:
    """→ (sevkiyatlar, malzemeler, taraflar, eşleşme yolu parçaları). Sırayla Takip No, PO, gemi adı."""
    sv_rows = data.rows("Sevkiyatlar")
    sev, yol, taraf = [], [], []

    def ekle(r, ac, tarafkol):
        if r["Sevkiyat No"] not in sev:
            sev.append(r["Sevkiyat No"])
            yol.append(f"{ac} → Sevkiyatlar → {r['Sevkiyat No']}")
        if r.get(tarafkol) and r[tarafkol] not in taraf:
            taraf.append(r[tarafkol])

    for t in c.takip_no_ipuclari:
        for r in sv_rows:
            if _n(r.get("Takip No (Sahte)")) == _n(t):
                ekle(r, f"Takip No {t} → Takip No (Sahte)", "Taşıyıcı No")
    for p in c.po_ipuclari:
        for r in sv_rows:
            if str(r.get("PO No") or "").strip() == str(p).strip():
                ekle(r, f"PO {p} → PO No", "Tedarikçi No")
    for g in c.gemi_adlari:
        for r in sv_rows:
            if _n(g) and _n(g) in _n(r.get("Son Konum / Not")):
                ekle(r, f"Gemi {g} → Son Konum / Not", "Taşıyıcı No")
    mlz = []
    for s in sev:
        for r in sv_rows:
            if r["Sevkiyat No"] == s and r["Malzeme No"] and r["Malzeme No"] not in mlz:
                mlz.extend(m for m in str(r["Malzeme No"]).split("; ") if m not in mlz)
    # Taraf adları → kimlik
    for tab, ad_k, no_k in (("Tedarikciler", "Tedarikçi Adı (Sahte)", "Tedarikçi No"),
                            ("Tasiyicilar", "Taşıyıcı Adı (Sahte)", "Taşıyıcı No")):
        for r in data.rows(tab):
            for ad in c.taraf_adlari:
                if _n(ad) and (_n(ad) in _n(r[ad_k]) or _n(r[ad_k]) in _n(ad)) and r[no_k] not in taraf:
                    taraf.append(r[no_k])
    return sev, mlz, taraf, yol


def guvenilirlik(data, row) -> int:
    taban = None
    for r in data.rows("Risk_Kaynaklari"):
        if r["Kaynak Kodu"] == row.get("Kaynak Kodu"):
            taban = r["Taban Güvenilirlik (1-5)"]
    if taban is None:
        taban = row.get("Kaynak Taban Güvenilirlik") or 1
    return int(min(5, max(1, int(taban) + (1 if str(row.get("Doğrulandı mı?")).strip() == "Evet" else 0))))


def tespit_gecikmesi_saat(row) -> float | None:
    a, b = row.get("Yayın Zamanı"), row.get("Tespit Zamanı")
    if a is None or b is None:
        return None
    return round((pd.Timestamp(b) - pd.Timestamp(a)).total_seconds() / 3600, 4)


def gurultu_nedeni(row, eslesen_sevkiyat: list[str]) -> str | None:
    no = str(row["Sinyal No"])
    if no.endswith("H"):
        return "Kapatılmış sinyal (H ekli)"
    if no.startswith("SG-2610-"):
        return "Geçmiş dönem sinyali (SG-2610-*)"
    durum = row.get("Durum")
    if durum in AYIKLA_DURUM:
        return f"Durum = {durum}"
    if durum == "İzlemede" and not eslesen_sevkiyat:
        return "İzleme sinyali; açık bir sevkiyatla eşleşmedi"
    return None


def gecikme_capraz(data, sevkiyatlar: list[str], gun: float | None) -> str | None:
    if gun is None or not sevkiyatlar:
        return None
    for r in data.rows("Sevkiyatlar"):
        if r["Sevkiyat No"] == sevkiyatlar[0]:
            sap = r.get("ETA Sapması (gün)")
            if sap is None and r.get("Planlanan Varış (ETA)") is not None:
                sap = (pd.Timestamp(r["Güncel Tahmini / Gerçekleşen Varış"]) - pd.Timestamp(r["Planlanan Varış (ETA)"])).days
            if sap is not None and abs(float(sap) - gun) > 0.01:
                return f"Metindeki gecikme {gun} gün, {r['Sevkiyat No']} ETA sapması {sap} gün"
    return None


def grupla(eslesmeler: dict[str, list[str]]) -> dict[str, str]:
    """Sinyal → grup anahtarı (ilk eşleşen sevkiyat). Aynı sevkiyata bağlananlar aynı risk kaydına."""
    return {s: sv[0] for s, sv in eslesmeler.items() if sv}
