"""SCOPE §7.1 koruma testi: cevap anahtarı, S1 cevap sabitleri ve Bedrock dışı LLM SDK'ları src/'de olmamalı."""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
YASAK = [r"nexus_answer_key", r"\b2741018\b", r"\b109567\b", r"\b108745\b", r"\b2291018\b",
         r"^\s*(import|from)\s+(openai|anthropic|google\.generativeai|ollama)\b"]


def test_src_temiz():
    ihlal = []
    for p in SRC.rglob("*.py"):
        t = p.read_text(encoding="utf-8")
        for y in YASAK:
            if re.search(y, t, re.M):
                ihlal.append(f"{p.relative_to(SRC)}: {y}")
    assert not ihlal, ihlal


def test_sema_import():
    from src.contracts import schemas
    assert schemas.SEMA_VERSIYONU == "1.1"


def test_veri_15_sayfa():
    from src.data_access.loader import load_data
    d = load_data()
    assert len(d.sheets) == 15 and str(d.d0) == "2026-11-25"
    assert isinstance(d.sheet("Sevkiyatlar")["PO No"].dropna().iloc[0], str)
