"""api Lambda (Function URL) — UI arka ucu (SCOPE §4.8). Hesap yapmaz; S3'ten okur.

GET  /runs              son run'lar (summary.json)
GET  /runs/{run_id}     runs/<run_id>/ altındaki tüm agent JSON'ları
GET  /decisions         decisions/*.json
POST /decision          {olay_no, karar, onaylayan_rol?, revize_notu?, yanlis_alarm?} -> AgentCore INSAN_KARARI
POST /email             {metin} veya {eml} -> inbound-email/ (yedek tetik)
Yetki: x-api-key başlığı == env API_KEY.
"""
from __future__ import annotations

import base64
import hmac
import json
import os
import uuid
from datetime import datetime, timezone

import boto3

BUCKET = os.environ.get("NEXUS_BUCKET", "")
API_KEY = os.environ.get("API_KEY", "")
RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN", "")
AGENTLAR = ("signal", "risk", "impact", "options", "decision")
KARARLAR = {"Onayla": "Onaylandı", "Reddet": "Reddedildi", "Değiştir": "Revize Edildi",
            "Onaylandı": "Onaylandı", "Reddedildi": "Reddedildi", "Revize Edildi": "Revize Edildi"}
MAX_RUNS = int(os.environ.get("MAX_RUNS", "50"))

s3 = boto3.client("s3")
CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "content-type,x-api-key",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def _yanit(kod: int, govde) -> dict:
    return {"statusCode": kod, "headers": {"Content-Type": "application/json; charset=utf-8", **CORS},
            "body": json.dumps(govde, ensure_ascii=False, default=str)}


def _json(key: str):
    try:
        return json.loads(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())
    except Exception as exc:
        if "NoSuchKey" in str(exc) or "Not Found" in str(exc):
            return None
        raise


def _listele(prefix: str, delimiter: str | None = None):
    kw = {"Bucket": BUCKET, "Prefix": prefix}
    if delimiter:
        kw["Delimiter"] = delimiter
    for sayfa in s3.get_paginator("list_objects_v2").paginate(**kw):
        yield sayfa


def runs_listesi() -> list[dict]:
    ozetler = []
    for sayfa in _listele("runs/"):
        for o in sayfa.get("Contents", []):
            if o["Key"].endswith("/summary.json"):
                ozetler.append(o)
    ozetler.sort(key=lambda o: o["LastModified"], reverse=True)
    sonuc = []
    for o in ozetler[:MAX_RUNS]:
        ozet = _json(o["Key"]) or {}
        ozet.setdefault("run_id", o["Key"].split("/")[1])
        ozet["_guncelleme"] = o["LastModified"].isoformat()
        sonuc.append(ozet)
    return sonuc


def run_detay(run_id: str) -> dict:
    if "/" in run_id or ".." in run_id:
        raise ValueError("geçersiz run_id")
    detay = {"run_id": run_id}
    for sayfa in _listele(f"runs/{run_id}/"):
        for o in sayfa.get("Contents", []):
            ad = o["Key"].rsplit("/", 1)[-1]
            if ad.endswith(".json"):
                detay[ad[:-5]] = _json(o["Key"])
    return detay


def kararlar() -> list[dict]:
    sonuc = []
    for sayfa in _listele("decisions/"):
        for o in sayfa.get("Contents", []):
            if o["Key"].endswith(".json"):
                k = _json(o["Key"])
                if k:
                    sonuc.append(k)
    sonuc.sort(key=lambda k: str(k.get("olay_no", "")), reverse=True)
    return sonuc


def agentcore(payload: dict) -> dict:
    if not RUNTIME_ARN:
        return {"durum": "HATA", "hata": "AGENT_RUNTIME_ARN tanımlı değil"}
    yanit = boto3.client("bedrock-agentcore").invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN, runtimeSessionId=f"nexus-ui-{uuid.uuid4().hex}",
        payload=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    g = yanit.get("response")
    metin = g.read().decode("utf-8") if hasattr(g, "read") else str(g)
    try:
        return json.loads(metin)
    except ValueError:
        return {"ham": metin[:2000]}


def karar_ver(govde: dict) -> dict:
    karar = KARARLAR.get(str(govde.get("karar", "")))
    if not govde.get("olay_no") or not karar:
        raise ValueError("olay_no ve karar (Onayla/Reddet/Değiştir) zorunlu")
    if karar == "Revize Edildi" and not (govde.get("revize_notu") or "").strip():
        raise ValueError("Değiştir için not zorunlu")
    payload = {
        "eylem": "INSAN_KARARI",
        "olay_no": govde["olay_no"],
        "karar": karar,
        "onaylayan_rol": govde.get("onaylayan_rol") or "Satınalmacı",  # rol, kişi adı değil (D16)
        "karar_zamani": datetime.now(timezone.utc).isoformat(),
        "revize_notu": govde.get("revize_notu"),
        "yanlis_alarm": bool(govde.get("yanlis_alarm", False)) and karar == "Reddedildi",
    }
    return agentcore(payload)


def eposta_yukle(govde: dict) -> dict:
    if govde.get("eml_base64"):
        veri = base64.b64decode(govde["eml_base64"]); uzanti = "eml"
    elif govde.get("eml"):
        veri = str(govde["eml"]).encode("utf-8"); uzanti = "eml"
    elif (govde.get("metin") or "").strip():
        veri = govde["metin"].encode("utf-8"); uzanti = "txt"
    else:
        raise ValueError("metin veya eml zorunlu")
    key = f"inbound-email/ui-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}.{uzanti}"
    s3.put_object(Bucket=BUCKET, Key=key, Body=veri, ContentType="message/rfc822" if uzanti == "eml" else "text/plain")
    return {"durum": "YUKLENDI", "key": key}


def lambda_handler(event, context):
    http = (event.get("requestContext") or {}).get("http") or {}
    yontem = http.get("method") or event.get("httpMethod") or "GET"
    yol = (http.get("path") or event.get("rawPath") or event.get("path") or "/").rstrip("/") or "/"
    if yontem == "OPTIONS":
        return _yanit(204, {})
    basliklar = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if not API_KEY or not hmac.compare_digest(basliklar.get("x-api-key", ""), API_KEY):
        return _yanit(401, {"hata": "yetkisiz"})
    try:
        govde = {}
        if event.get("body"):
            ham = base64.b64decode(event["body"]) if event.get("isBase64Encoded") else event["body"]
            govde = json.loads(ham)
        parcalar = [p for p in yol.split("/") if p]
        if yontem == "GET" and parcalar == ["runs"]:
            return _yanit(200, {"runs": runs_listesi()})
        if yontem == "GET" and len(parcalar) == 2 and parcalar[0] == "runs":
            return _yanit(200, run_detay(parcalar[1]))
        if yontem == "GET" and parcalar == ["decisions"]:
            return _yanit(200, {"decisions": kararlar()})
        if yontem == "POST" and parcalar == ["decision"]:
            return _yanit(200, karar_ver(govde))
        if yontem == "POST" and parcalar == ["email"]:
            return _yanit(200, eposta_yukle(govde))
        if yontem == "GET" and parcalar in ([], ["health"]):
            return _yanit(200, {"durum": "OK"})
        return _yanit(404, {"hata": f"bulunamadı: {yontem} {yol}"})
    except ValueError as exc:
        return _yanit(400, {"hata": str(exc)})
    except Exception as exc:
        return _yanit(500, {"hata": str(exc)})
