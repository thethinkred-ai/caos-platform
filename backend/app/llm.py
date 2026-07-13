"""OpenAI-compatible LLM adapter with stub fallback."""

import json
import logging

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def is_llm_available() -> bool:
    return bool(settings.ai_api_key)


async def llm_complete(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """Call an OpenAI-compatible chat completions endpoint.

    Returns the assistant message content, or empty string on error.
    """
    if not is_llm_available():
        return ""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.ai_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.ai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.ai_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": 800,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
        return ""


def llm_complete_sync(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """Synchronous wrapper for llm_complete."""
    if not is_llm_available():
        return ""

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{settings.ai_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.ai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.ai_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": 800,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
        return ""
