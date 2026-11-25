#!/usr/bin/env python3
"""Demo hazırlığı (SCOPE D17): S3 durumunu temizler, ardından canlı sinyaller hariç toplu tarama çalıştırır.

Kullanım: python scripts/demo_reset.py [--yalnizca-temizle] [--evet]
Ortam: NEXUS_BUCKET (yoksa nexus-<hesap>-<bölge>), AGENT_RUNTIME_ARN, DEMO_CANLI_SINYALLER.
input/ dokunulmaz.
"""
import argparse
import json
import os
import uuid

import boto3

ONEKLER = ["runs/", "registry/", "decisions/", "signals/", "inbound-email/", "exports/"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yalnizca-temizle", action="store_true")
    ap.add_argument("--evet", action="store_true", help="onay sormadan sil")
    a = ap.parse_args()
    region = os.environ.get("AWS_REGION", "us-east-1")
    hesap = boto3.client("sts").get_caller_identity()["Account"]
    bucket = os.environ.get("NEXUS_BUCKET") or f"nexus-{hesap}-{region}"
    if not a.evet and input(f"s3://{bucket}/ altında {ONEKLER} silinecek. Devam? [e/H] ").lower() != "e":
        return
    s3 = boto3.client("s3", region_name=region)
    for onek in ONEKLER:
        n = 0
        for sayfa in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=onek):
            anahtarlar = [{"Key": o["Key"]} for o in sayfa.get("Contents", [])]
            if anahtarlar:
                s3.delete_objects(Bucket=bucket, Delete={"Objects": anahtarlar})
                n += len(anahtarlar)
        print(f"{onek}: {n} nesne silindi")
    if a.yalnizca_temizle:
        return
    arn = os.environ.get("AGENT_RUNTIME_ARN")
    if not arn:
        print("AGENT_RUNTIME_ARN yok; toplu tarama atlandı.")
        return
    haric = [s.strip() for s in os.environ.get("DEMO_CANLI_SINYALLER", "SG-2611-001,SG-2611-002").split(",") if s.strip()]
    ac = boto3.client("bedrock-agentcore", region_name=region,
                      config=boto3.session.Config(read_timeout=900, retries={"max_attempts": 1}))
    print(f"TOPLU_TARAMA (hariç: {haric}) çalışıyor…")
    r = ac.invoke_agent_runtime(agentRuntimeArn=arn, runtimeSessionId=f"nexus-demo-reset-{uuid.uuid4().hex}",
                                payload=json.dumps({"eylem": "TOPLU_TARAMA", "haric": haric}).encode())
    print(r["response"].read().decode()[:3000])


if __name__ == "__main__":
    main()
