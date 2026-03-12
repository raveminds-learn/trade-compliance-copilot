import requests
from config.settings import settings
from config.logger import get_logger

log = get_logger("EXPLAINER")


def generate_explanation(
    *,
    pattern: str,
    trader_id: str,
    instrument: str,
    evidence: str,
    confidence: int,
    similar_count: int,
) -> str:
    prompt = (
        f"You are a trade surveillance AI. Write 2-3 sentences for a compliance officer. "
        f"Be direct and factual. No preamble.\n\n"
        f"Trader: {trader_id}, Instrument: {instrument}\n"
        f"Pattern: {pattern}\n"
        f"Finding: {evidence}\n"
        f"Confidence: {confidence}. Similar historical cases: {similar_count}."
    )

    try:
        resp = requests.post(
            f"{settings.OLLAMA_HOST}/api/generate",
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        log.warning("LLM unavailable — using rule evidence: %s", e)
        return evidence or f"Suspicious {pattern} detected for {trader_id}."
