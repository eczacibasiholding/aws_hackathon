"""GİRDİ Excel'ini bir kez yükler (nexus-data.md §4, §8, §9; orkestratör veri kuralları §1).

Kaynak: NEXUS_INPUT_URI (yerel yol ya da s3://bucket/key). Varsayılan: data/nexus_agent_input.xlsx.
Cevap anahtarı burada ASLA okunmaz (KÇ6).
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

VARSAYILAN_GIRDI = str(Path(__file__).resolve().parents[2] / "data" / "nexus_agent_input.xlsx")
STRING_SUTUNLAR = {"PO No": str}


@dataclass
class NexusData:
    sheets: dict[str, pd.DataFrame]
    params: dict[str, Any]
    d0: date
    kaynak: str
    extra_signals: list[dict] = field(default_factory=list)  # signals/ altındaki e-posta sinyalleri (§4.5)

    def sheet(self, ad: str) -> pd.DataFrame:
        return self.sheets[ad]

    def rows(self, ad: str) -> list[dict]:
        return self.sheets[ad].to_dict(orient="records")

    def param(self, ad: str) -> Any:
        if ad not in self.params:
            raise KeyError(f"Parametreler sayfasında '{ad}' yok")
        return self.params[ad]


def _oku_bytes(uri: str) -> bytes:
    if uri.startswith("s3://"):
        import boto3

        bucket, key = uri[5:].split("/", 1)
        return boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
    return Path(uri).read_bytes()


def _temizle(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all")
    df = df.astype(object).where(pd.notna(df), None)
    return df.map(lambda v: None if isinstance(v, str) and v.strip() == "-" else v)


def load_data(uri: str | None = None) -> NexusData:
    uri = uri or os.environ.get("NEXUS_INPUT_URI") or VARSAYILAN_GIRDI
    raw = pd.read_excel(io.BytesIO(_oku_bytes(uri)), sheet_name=None, dtype=STRING_SUTUNLAR)
    raw.pop("00_Rehber", None)
    sheets = {ad: _temizle(df) for ad, df in raw.items()}
    params = dict(zip(sheets["Parametreler"]["Parametre"], sheets["Parametreler"]["Değer"]))
    d0 = pd.Timestamp(params["AnalizTarihi"]).date()
    return NexusData(sheets=sheets, params=params, d0=d0, kaynak=uri)


@lru_cache(maxsize=2)
def load_cached(uri: str | None = None) -> NexusData:
    return load_data(uri)
