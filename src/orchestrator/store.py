"""Durum deposu: S3 (NEXUS_BUCKET) ya da yerel klasör (NEXUS_STATE_DIR, varsayılan .state/). SCOPE §4.6."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class Store:
    def __init__(self):
        self.bucket = os.environ.get("NEXUS_BUCKET")
        self.root = Path(os.environ.get("NEXUS_STATE_DIR", ".state"))
        self._s3 = None
        if self.bucket:
            import boto3

            self._s3 = boto3.client("s3")

    def put(self, key: str, obj: Any) -> None:
        body = json.dumps(obj, ensure_ascii=False, indent=1, default=str).encode()
        if self._s3:
            self._s3.put_object(Bucket=self.bucket, Key=key, Body=body, ContentType="application/json")
        else:
            p = self.root / key
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            if self._s3:
                return json.loads(self._s3.get_object(Bucket=self.bucket, Key=key)["Body"].read())
            return json.loads((self.root / key).read_text())
        except Exception:
            return default

    def list(self, prefix: str) -> list[str]:
        if self._s3:
            out, tok = [], None
            while True:
                kw = {"Bucket": self.bucket, "Prefix": prefix, **({"ContinuationToken": tok} if tok else {})}
                r = self._s3.list_objects_v2(**kw)
                out += [o["Key"] for o in r.get("Contents", [])]
                if not r.get("IsTruncated"):
                    return out
                tok = r["NextContinuationToken"]
        base = self.root / prefix
        if not base.exists():
            return []
        return [str(p.relative_to(self.root)) for p in base.rglob("*") if p.is_file()]
