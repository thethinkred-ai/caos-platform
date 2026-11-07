"""OpenAI-compatible LLM adapter with a fallback chain and stub fallback.

Модели перебираются по порядку: основная из AI_MODEL, затем резервные из
AI_FALLBACK_MODELS (через запятую). Бесплатные модели на OpenRouter регулярно
отвечают 429/503, поэтому одна модель без резерва = пустые ответы в интерфейсе.
Первый содержательный ответ возвращается, а имя ответившей модели запоминается
в LAST_MODEL — чтобы в базе не записывалось, будто ответила основная модель.
"""

import logging
import time

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Какая модель реально ответила в последний успешный вызов.
LAST_MODEL: str = ""


def _model_chain() -> list[str]:
    chain = [settings.ai_model]
    for raw in (settings.ai_fallback_models or "").split(","):
        name = raw.strip()
        if name and name not in chain:
            chain.append(name)
    return chain


def llm_source() -> str:
    """Метка источника для записи предложения — по фактически ответившей модели."""
    return f"llm:{LAST_MODEL or settings.ai_model}"


def is_llm_available() -> bool:
    return bool(settings.ai_api_key)


def _payload(model: str, system_prompt: str, user_prompt: str, temperature: float) -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": 800,
    }


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }


def _extract(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    return (choices[0].get("message", {}).get("content") or "").strip()


async def llm_complete(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """Call an OpenAI-compatible chat completions endpoint.

    Returns the assistant message content, or empty string on error.
    """
    global LAST_MODEL
    if not is_llm_available():
        return ""

    # Бюджет на всю цепочку: столько ждёт эндпоинт. Отдельной модели даём не
    # больше 15 с — иначе медленная первая съедает весь бюджет и резерв не
    # успевает ответить.
    budget = 30.0
    per_model = 15.0
    deadline = time.monotonic() + budget

    async with httpx.AsyncClient(timeout=budget) as client:
        for model in _model_chain():
            left = deadline - time.monotonic()
            if left < 3:
                break
            try:
                resp = await client.post(
                    f"{settings.ai_base_url}/chat/completions",
                    headers=_headers(),
                    json=_payload(model, system_prompt, user_prompt, temperature),
                    timeout=min(left, per_model),
                )
                resp.raise_for_status()
                text = _extract(resp.json())
                if text:
                    LAST_MODEL = model
                    return text
                logger.warning("LLM %s: пустой ответ, пробую следующую", model)
            except Exception as exc:
                logger.warning("LLM %s failed: %s", model, exc)
    return ""


def llm_complete_sync(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """Synchronous wrapper for llm_complete."""
    global LAST_MODEL
    if not is_llm_available():
        return ""

    budget = 30.0
    per_model = 15.0
    deadline = time.monotonic() + budget

    with httpx.Client(timeout=budget) as client:
        for model in _model_chain():
            left = deadline - time.monotonic()
            if left < 3:
                break
            try:
                resp = client.post(
                    f"{settings.ai_base_url}/chat/completions",
                    headers=_headers(),
                    json=_payload(model, system_prompt, user_prompt, temperature),
                    timeout=min(left, per_model),
                )
                resp.raise_for_status()
                text = _extract(resp.json())
                if text:
                    LAST_MODEL = model
                    return text
                logger.warning("LLM %s: пустой ответ, пробую следующую", model)
            except Exception as exc:
                logger.warning("LLM %s failed: %s", model, exc)
    return ""
