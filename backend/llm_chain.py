"""Multi-provider LLM chain with retries, fallback, and response caching.

Providers expose an async ``complete(prompt)`` method returning the generated
text and raise :class:`ProviderError` on any failure (missing key, HTTP error,
unexpected payload).  :func:`generate` walks the configured fallback chain,
retrying each provider with exponential backoff.
"""

import asyncio
import logging
import os
from typing import Awaitable, Callable, Optional

import aiohttp

from backend.cache import TTLCache
from backend.config import (
    CACHE_TTL_SECONDS,
    LLM_FALLBACK_CHAIN,
    LLM_MAX_RETRIES,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Raised when an LLM provider call fails."""


class LLMUnavailableError(RuntimeError):
    """Raised when every provider in the fallback chain has failed."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("All providers failed: " + "; ".join(errors))
        self.errors = errors


def _require_api_key(provider: str) -> str:
    env_name = f"{provider.upper()}_API_KEY"
    key = os.getenv(env_name)
    if not key:
        raise ProviderError(f"{provider} key missing ({env_name})")
    return key


async def _post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
) -> tuple[int, object]:
    timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload, headers=headers or {}) as resp:
            body = await resp.text()
            if resp.status != 200:
                raise ProviderError(f"HTTP {resp.status}: {body[:200]}")
            try:
                return resp.status, await resp.json()
            except Exception as exc:  # noqa: BLE001 - surface parse failures
                raise ProviderError(f"Invalid JSON response: {exc}") from exc


def _openai_style_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _extract_openai_content(data: object, provider: str) -> str:
    try:
        return data["choices"][0]["message"]["content"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(f"Unexpected {provider} response shape") from exc


class OpenAICompatibleProvider:
    """Provider speaking the OpenAI chat-completions wire format."""

    def __init__(self, name: str, url: str, model: str) -> None:
        self.name = name
        self.url = url
        self.model = model

    async def complete(self, prompt: str) -> str:
        api_key = _require_api_key(self.name)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": LLM_TEMPERATURE,
        }
        _, data = await _post_json(self.url, payload, _openai_style_headers(api_key))
        return _extract_openai_content(data, self.name)


class HuggingFaceProvider:
    name = "huggingface"
    URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"

    async def complete(self, prompt: str) -> str:
        api_key = _require_api_key("HUGGINGFACE")
        _, data = await _post_json(
            self.URL, {"inputs": prompt}, _openai_style_headers(api_key)
        )
        if isinstance(data, list) and data:
            try:
                return data[0]["generated_text"]
            except (KeyError, TypeError) as exc:
                raise ProviderError("Unexpected HF response shape") from exc
        raise ProviderError("Unexpected HF response")


class GeminiProvider:
    name = "gemini"
    URL = (
        "https://generativelanguage.googleapis.com"
        "/v1beta/models/gemini-1.5-flash:generateContent"
    )

    async def complete(self, prompt: str) -> str:
        api_key = _require_api_key("GEMINI")
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": LLM_TEMPERATURE},
        }
        _, data = await _post_json(f"{self.URL}?key={api_key}", payload)
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]  # type: ignore[index]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Unexpected Gemini response shape") from exc


PROVIDERS: dict[str, object] = {
    "openrouter": OpenAICompatibleProvider(
        "OPENROUTER",
        "https://openrouter.ai/api/v1/chat/completions",
        "meta-llama/llama-3.1-8b-instruct:free",
    ),
    "groq": OpenAICompatibleProvider(
        "GROQ",
        "https://api.groq.com/openai/v1/chat/completions",
        "llama-3.1-8b-instant",
    ),
    "huggingface": HuggingFaceProvider(),
    "gemini": GeminiProvider(),
}

_response_cache = TTLCache(CACHE_TTL_SECONDS)


async def _call_with_retry(
    complete: Callable[[str], Awaitable[str]],
    prompt: str,
    max_retries: int = LLM_MAX_RETRIES,
) -> str:
    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return await complete(prompt)
        except Exception as exc:  # noqa: BLE001 - retried below
            last_error = exc
            if attempt < max_retries:
                await asyncio.sleep(2**attempt)
    assert last_error is not None
    raise last_error


async def generate(prompt: str) -> tuple[str, str]:
    """Generate a reply, returning ``(reply, provider_name)``.

    Checks the TTL cache first, then tries each provider in the fallback
    chain.  Raises :class:`LLMUnavailableError` if all providers fail.
    """
    cache_key = _response_cache.make_key(prompt)
    cached = _response_cache.get(cache_key)
    if cached is not None:
        return cached, "cache"

    errors: list[str] = []
    for name in LLM_FALLBACK_CHAIN:
        provider = PROVIDERS.get(name)
        if provider is None:
            errors.append(f"{name}: unknown provider")
            continue
        try:
            reply = await _call_with_retry(provider.complete, prompt)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001 - collect and fall through
            logger.warning("Provider %s failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
            continue
        _response_cache.set(cache_key, reply)
        return reply, name

    raise LLMUnavailableError(errors)
