"""AgentCore Runtime giriş noktası (SCOPE §4.7, karar D2: tek Runtime).

payload: {"eylem": "SINYAL_ISLE" | "TOPLU_TARAMA" | "INSAN_KARARI", ...}
"""
from __future__ import annotations

import logging

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from src.orchestrator.orchestrator import insan_karari, sinyal_isle, toplu_tarama

log = logging.getLogger("nexus.app")
app = BedrockAgentCoreApp()

EYLEMLER = {
    "SINYAL_ISLE": sinyal_isle,
    "TOPLU_TARAMA": toplu_tarama,
    "INSAN_KARARI": insan_karari,
}


@app.entrypoint
def invoke(payload, context=None):
    payload = payload or {}
    eylem = str(payload.get("eylem", "")).upper()
    fn = EYLEMLER.get(eylem)
    if fn is None:
        return {"durum": "HATA", "hata": f"Bilinmeyen eylem: {eylem!r}", "gecerli": sorted(EYLEMLER)}
    log.info("eylem=%s", eylem)
    try:
        return fn(payload)
    except Exception as exc:  # orkestratör kısmi sonucu kendisi yazar; burada yalnızca güvenli dönüş
        log.exception("eylem %s başarısız", eylem)
        return {"durum": "HATA", "eylem": eylem, "hata": str(exc)}


if __name__ == "__main__":
    app.run()
