"""Girdi Excel'inden harita taban verisini üretir ve S3'e yazar: map/base.json (SCOPE §4.6 kova düzeni).

Kullanım: NEXUS_BUCKET=... python scripts/build_map_data.py   (NEXUS_BUCKET yoksa yalnızca .build/map_base.json)
Konumlar ETD/ETA'dan API'de zamana göre hesaplanır (src/api/map_view.py). Hesap yapılmaz, veri taşınır.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_access.loader import load_data  # noqa: E402

TUR = {"Fabrika": "fabrika", "Depo": "depo", "Maden Sahası": "maden"}
MOD = {"Denizyolu": "deniz", "Havayolu": "hava", "Karayolu": "kara", "Demiryolu": "demiryolu"}


def temiz(v):
    return None if v is None or (isinstance(v, float) and v != v) else v


def iso(v):
    return None if v is None else str(v)[:10]


def main():
    d = load_data()
    k = json.loads((ROOT / "config" / "konumlar.json").read_text(encoding="utf-8"))
    nok, rotalar = k["noktalar"], k["deniz_rotalari"]
    ted = {r["Tedarikçi No"]: r for r in d.rows("Tedarikciler")}
    out = {}
    for t in d.rows("Tesisler"):
        o = out.setdefault(t["Kuruluş Kodu"], {"facilities": [], "shipments": []})
        o["facilities"].append({"id": t["Tesis Kodu"], "name": t["Tesis Adı"], "kind": TUR.get(t["Tesis Tipi"], "depo"),
                                "lon": float(t["Boylam"]), "lat": float(t["Enlem"]), "external": False})
    for s in d.rows("Sevkiyatlar"):
        o = out.setdefault(s["Kuruluş Kodu"], {"facilities": [], "shipments": []})
        cik, var = s["Çıkış Noktası"], s["Varış Noktası"]
        if cik not in nok or var not in nok:
            continue
        tid = ted.get(s["Tedarikçi No"], {})
        fid_c, fid_v = f"x-{cik}", f"x-{var}"
        hava = MOD.get(s["Taşıma Modu"]) == "hava"
        for fid, ad, kind, p in ((fid_c, f"{tid.get('Tedarikçi Adı (Sahte)', s['Tedarikçi No'])} · {cik}", "tedarikci", nok[cik]),
                                 (fid_v, var, "havalimani" if hava else "liman", nok[var])):
            if not any(f["id"] == fid for f in o["facilities"]):
                o["facilities"].append({"id": fid, "name": ad, "kind": kind, "lon": p[0], "lat": p[1], "external": True})
        o["shipments"].append({
            "id": s["Sevkiyat No"], "direction": "alis", "material": s["Malzeme Adı"], "quantity": s["Miktar"],
            "unit": s["Ölçü Birimi"], "mode": MOD.get(s["Taşıma Modu"]), "from": fid_c, "to": fid_v,
            "nihai_tesis": s["Nihai Varış Tesisi"], "durum_metni": s["Durum"],
            "departed_at": iso(s["Çıkış Tarihi (ETD)"]), "eta_planned": iso(s["Planlanan Varış (ETA)"]),
            "eta": iso(s["Güncel Tahmini / Gerçekleşen Varış"]), "delay_reason": temiz(s.get("Sapma Nedeni")),
            "not": temiz(s.get("Son Konum / Not")), "route": rotalar.get(f"{cik}>{var}") or [nok[cik], nok[var]],
        })
    body = json.dumps(out, ensure_ascii=False, default=str)
    (ROOT / ".build").mkdir(exist_ok=True)
    (ROOT / ".build" / "map_base.json").write_text(body, encoding="utf-8")
    if os.environ.get("NEXUS_BUCKET"):
        import boto3
        boto3.client("s3").put_object(Bucket=os.environ["NEXUS_BUCKET"], Key="map/base.json", Body=body.encode(),
                                      ContentType="application/json")
    print({k: len(v["shipments"]) for k, v in out.items()})


if __name__ == "__main__":
    main()
