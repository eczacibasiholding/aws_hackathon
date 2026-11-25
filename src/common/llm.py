"""Bedrock LLM çağrıları için tek giriş noktası (KÇ1, KÇ2, SCOPE §4.3).

Yalnızca Strands Agents + Amazon Bedrock kullanılır. Model kimliği BEDROCK_MODEL_ID'den okunur.
LLM yalnızca LLM sınır modellerini doldurur; sayı üretmez (KÇ7).

NEXUS_LLM=off ise (yerel deterministik testler) None döner; çağıran taraf uyarı üretip
deterministik yedekle devam eder (KÇ10).
"""
from __future__ import annotations

import logging
import os
from typing import TypeVar

from pydantic import BaseModel

log = logging.getLogger("nexus.llm")
T = TypeVar("T", bound=BaseModel)


def llm_acik() -> bool:
    return os.environ.get("NEXUS_LLM", "on").lower() not in {"off", "0", "false"} and bool(
        os.environ.get("BEDROCK_MODEL_ID")
    )


def _model():
    from strands.models import BedrockModel

    return BedrockModel(
        model_id=os.environ["BEDROCK_MODEL_ID"],
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        temperature=float(os.environ.get("NEXUS_LLM_TEMPERATURE", "0.1")),
    )


def structured(prompt: str, output_model: type[T], system: str, tools: list | None = None) -> T | None:
    """Strands agent'ı ile yapılandırılmış çıktı. Hata/kapalıysa None (çağıran uyarı ekler)."""
    if not llm_acik():
        return None
    try:
        from strands import Agent

        agent = Agent(model=_model(), system_prompt=system, tools=tools or [], callback_handler=None)
        return agent.structured_output(output_model, prompt)
    except Exception as e:  # Bedrock/ağ/doğrulama hatası → kısmi sonuç
        log.warning("LLM çağrısı başarısız: %s", e)
        return None


def text(prompt: str, system: str) -> str | None:
    if not llm_acik():
        return None
    try:
        from strands import Agent

        agent = Agent(model=_model(), system_prompt=system, callback_handler=None)
        return str(agent(prompt)).strip()
    except Exception as e:
        log.warning("LLM metin çağrısı başarısız: %s", e)
        return None
