"""email_trigger Lambda (SCOPE §4.4, §4.5, karar D6).

S3 ObjectCreated (inbound-email/) -> MIME ayrıştır -> PII temizle -> sinyal eşleştir / yeni sinyal
-> registry/processed.json (idempotency) -> AgentCore InvokeAgentRuntime {eylem: SINYAL_ISLE}.
Bağımlılık: boto3 + openpyxl (pandas yok). Kişisel veri loglanmaz (KÇ5).
"""
from __future__ import annotations

import email
import io
import json
import logging
import os
import re
import unicodedata
import urllib.parse
import uuid
from datetime import datetime, timezone
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

import boto3

log = logging.getLogger()
log.setLevel(logging.INFO)

BUCKET = os.environ.get("NEXUS_BUCKET", "")
INPUT_KEY = os.environ.get("NEXUS_INPUT_KEY", "input/nexus_agent_input.xlsx")
RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN", "")
PROCESSED_KEY = "registry/processed.json"
SINYAL_DESEN = re.compile(r"^SG-2611-(\d{3})$")
HAM_METIN_SUTUN = "Ham Metin (LLM Girdisi)"
META_SUTUNLAR = ["Kaynak Kodu", "Kaynak Taban Güvenilirlik", "Doğrulandı mı?", "Yayın Zamanı", "Tespit Zamanı", "Dil"]

s3 = boto3.client("s3")

# ---------- PII temizliği ----------
EPOSTA_RE = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
TELEFON_RE = re.compile(r"(?<![\w-])\+?\d[\d\s().-]{7,}\d(?![\w-])")
IMZA_BASLANGIC = re.compile(
    r"^\s*(--\s*$|best regards|kind regards|regards,?$|saygılarımla|saygilarimla|iyi çalışmalar|thanks,?$|sent from my)",
    re.IGNORECASE,
)
ALINTI_RE = re.compile(r"^\s*(>|On .+ wrote:)")


def pii_temizle(govde: str) -> str:
    satirlar = []
    for satir in govde.replace("\r\n", "\n").split("\n"):
        if IMZA_BASLANGIC.match(satir) or ALINTI_RE.match(satir):
            break  # imza / alıntı bloğu ve sonrası atılır
        satirlar.append(satir)
    metin = "\n".join(satirlar)
    metin = EPOSTA_RE.sub("[e-posta]", metin)
    metin = TELEFON_RE.sub(lambda m: m.group(0) if _tarih_benzeri(m.group(0)) else "[telefon]", metin)
    return metin.strip()


def _tarih_benzeri(s: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", s.strip()))


def normalize(metin: str) -> str:
    metin = unicodedata.normalize("NFKC", metin or "")
    metin = metin.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", metin).strip().casefold()


# ---------- MIME ----------
def mime_ayristir(ham: bytes) -> dict:
    msg = email.message_from_bytes(ham, policy=policy.default)
    govde = ""
    if msg.is_multipart():
        parca = msg.get_body(preferencelist=("plain", "html"))
        if parca is not None:
            govde = parca.get_content()
    elif msg.get_content_type() in ("text/plain", "text/html") and (msg.keys() or msg.get_payload()):
        govde = msg.get_content()
    if not msg.keys():  # başlıksız düz metin (yedek tetik)
        govde = ham.decode("utf-8", errors="replace")
    if "<html" in govde.lower():
        govde = re.sub(r"<[^>]+>", " ", govde)
    tarih = None
    if msg.get("Date"):
        try:
            tarih = parsedate_to_datetime(str(msg["Date"]))
        except (TypeError, ValueError):
            tarih = None
    alan = parseaddr(str(msg.get("From", "")))[1].rsplit("@", 1)[-1].lower() if msg.get("From") else None
    return {"govde": govde, "tarih": tarih, "gonderen_alan": alan or None}


# ---------- Girdi sinyalleri ----------
def _girdi_sinyalleri() -> list[dict]:
    import openpyxl  # Lambda paketinde

    obj = s3.get_object(Bucket=BUCKET, Key=INPUT_KEY)
    wb = openpyxl.load_workbook(io.BytesIO(obj["Body"].read()), read_only=True, data_only=True)
    ws = wb["Risk_Sinyalleri"]
    satirlar = ws.iter_rows(values_only=True)
    baslik = [str(h).strip() if h is not None else "" for h in next(satirlar)]
    kayitlar = []
    for r in satirlar:
        if not r or r[0] is None:
            continue
        kayitlar.append({baslik[i]: r[i] for i in range(min(len(baslik), len(r)))})
    return kayitlar


def _iso(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def _kaynak_eslemesi() -> dict:
    yol = Path(__file__).with_name("email_kaynaklari.yaml")
    if not yol.exists():
        yol = Path(__file__).resolve().parents[3] / "config" / "email_kaynaklari.yaml"
    esleme = {}
    if yol.exists():  # basit YAML okuyucu (PyYAML bağımlılığı yok): "alan: KYxx"
        for satir in yol.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s+([\w.-]+):\s*(KY\d+)", satir)
            if m:
                esleme[m.group(1).lower()] = m.group(2)
    return esleme


def _json_oku(key: str, varsayilan):
    try:
        return json.loads(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())
    except s3.exceptions.NoSuchKey:
        return varsayilan
    except Exception as exc:  # AccessDenied vb. -> varsayılan
        if "NoSuchKey" in str(exc):
            return varsayilan
        raise


def _json_yaz(key: str, veri) -> None:
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(veri, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
                  ContentType="application/json")


def _yeni_sinyal_no(girdi: list[dict]) -> str:
    enb = 0
    for r in girdi:
        m = SINYAL_DESEN.match(str(r.get("Sinyal No", "")))
        if m:
            enb = max(enb, int(m.group(1)))
    pag = s3.get_paginator("list_objects_v2")
    for sayfa in pag.paginate(Bucket=BUCKET, Prefix="signals/"):
        for o in sayfa.get("Contents", []):
            m = SINYAL_DESEN.match(o["Key"].rsplit("/", 1)[-1].removesuffix(".json"))
            if m:
                enb = max(enb, int(m.group(1)))
    return f"SG-2611-{enb + 1:03d}"


def sinyal_kaydi_uret(temiz: str, mime: dict, olusma: datetime) -> tuple[str, bool, list[dict]]:
    """(sinyal_no, yeni_mi, uyarilar)."""
    girdi = _girdi_sinyalleri()
    hedef = normalize(temiz)
    for r in girdi:
        if normalize(str(r.get(HAM_METIN_SUTUN) or "")) == hedef and hedef:
            return str(r["Sinyal No"]), False, []
    uyarilar = []
    kaynak_kodu = _kaynak_eslemesi().get(mime.get("gonderen_alan") or "")
    if kaynak_kodu is None:
        uyarilar.append({"kod": "ESLESME_YOK", "mesaj": "Gönderen alan adı email_kaynaklari.yaml'da yok", "alan": "Kaynak Kodu"})
    no = _yeni_sinyal_no(girdi)
    kayit = {
        "Sinyal No": no,
        "Yayın Zamanı": _iso(mime.get("tarih") or olusma),
        "Tespit Zamanı": _iso(olusma),
        "Kaynak Kodu": kaynak_kodu,
        "Kaynak Taban Güvenilirlik": None,
        "Kategori": None,
        "Dil": None,
        HAM_METIN_SUTUN: temiz,
        "Doğrulandı mı?": "Hayır",
        "Durum": "Açık – Analizde",
        "kaynak": "EMAIL",
        "uyarilar": uyarilar,
    }
    _json_yaz(f"signals/{no}.json", kayit)
    return no, True, uyarilar


def agentcore_cagir(payload: dict, oturum: str | None = None) -> dict:
    if not RUNTIME_ARN:
        log.warning("AGENT_RUNTIME_ARN tanımlı değil; çağrı atlandı")
        return {"atlandi": True}
    ac = boto3.client("bedrock-agentcore")
    oturum = oturum or f"nexus-{uuid.uuid4().hex}"  # >= 33 karakter
    yanit = ac.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=oturum,
        payload=json.dumps(payload).encode("utf-8"),
    )
    govde = yanit.get("response")
    metin = govde.read().decode("utf-8") if hasattr(govde, "read") else str(govde)
    try:
        return json.loads(metin)
    except ValueError:
        return {"ham": metin[:2000]}


def nesne_isle(bucket: str, key: str) -> dict:
    global BUCKET
    BUCKET = BUCKET or bucket
    islenen = _json_oku(PROCESSED_KEY, {"nesneler": {}, "sinyaller": {}})
    islenen.setdefault("nesneler", {}); islenen.setdefault("sinyaller", {})
    if key in islenen["nesneler"]:
        log.info("zaten işlendi: %s", key)
        return {"durum": "ATLANDI", "neden": "idempotent", **islenen["nesneler"][key]}

    obj = s3.get_object(Bucket=bucket, Key=key)
    olusma = obj.get("LastModified") or datetime.now(timezone.utc)
    mime = mime_ayristir(obj["Body"].read())
    temiz = pii_temizle(mime["govde"])
    if not temiz:
        return {"durum": "ATLANDI", "neden": "bos_govde"}
    sinyal_no, yeni, uyarilar = sinyal_kaydi_uret(temiz, mime, olusma)
    log.info("sinyal=%s yeni=%s uyari=%s", sinyal_no, yeni, [u["kod"] for u in uyarilar])  # gövde loglanmaz

    kayit = {"sinyal_no": sinyal_no, "yeni": yeni, "zaman": datetime.now(timezone.utc).isoformat()}
    islenen["nesneler"][key] = kayit
    islenen["sinyaller"][sinyal_no] = {"kaynak_nesne": key, **kayit}
    _json_yaz(PROCESSED_KEY, islenen)  # çağrıdan önce: tekrar teslimde ikinci çağrı olmaz

    sonuc = agentcore_cagir({"eylem": "SINYAL_ISLE", "sinyal_no": sinyal_no, "kaynak": "EMAIL"})
    return {"durum": "TAMAM", "sinyal_no": sinyal_no, "yeni": yeni,
            "run_id": sonuc.get("run_id") if isinstance(sonuc, dict) else None}


def lambda_handler(event, context):
    sonuclar = []
    for rec in event.get("Records", []):
        b = rec["s3"]["bucket"]["name"]
        k = urllib.parse.unquote_plus(rec["s3"]["object"]["key"])
        if not k.startswith("inbound-email/") or k.endswith("/"):
            continue
        sonuclar.append(nesne_isle(b, k))
    return {"sonuclar": sonuclar}
