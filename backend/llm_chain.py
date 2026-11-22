"""Multi-provider LLM chain with retries, fallback, and response caching.

Every provider/model pair declared in :mod:`backend.providers` is tried in the
configured fallback order; within a provider each free model is attempted
before falling through to the next provider.  Providers expose an async
``complete(prompt)`` method returning generated text and raise
:class:`ProviderError` on any failure (missing key, HTTP error, unexpected
payload).  :func:`generate` walks the chain and raises
:class:`LLMUnavailableError` only when every option has failed.
"""

import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Optional

import aiohttp

from backend.cache import TTLCache
from backend.config import (
    CACHE_TTL_SECONDS,
    LLM_FALLBACK_CHAIN,
    LLM_MAX_RETRIES,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
)
from backend.providers import PROVIDERS

logger = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Raised when an LLM provider call fails."""


class LLMUnavailableError(RuntimeError):
    """Raised when every provider/model in the fallback chain has failed."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("All providers failed: " + "; ".join(errors[:12]))
        self.errors = errors


def _require_api_key(env_name: str) -> str:
    key = os.getenv(env_name)
    if not key:
        raise ProviderError(f"API key missing ({env_name})")
    return key


async def _post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
) -> Any:
    timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload, headers=headers or {}) as resp:
            body = await resp.text()
            if resp.status != 200:
                raise ProviderError(f"HTTP {resp.status}: {body[:200]}")
            try:
                return await resp.json()
            except Exception as exc:  # noqa: BLE001 - surface parse failures
                raise ProviderError(f"Invalid JSON response: {exc}") from exc


def _bearer_headers(api_key: str, extra: Optional[dict] = None) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if extra:
        headers.update(extra)
    return headers


def _extract_openai_content(data: Any, provider: str) -> str:
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(f"Unexpected {provider} response shape") from exc


class ModelEndpoint:
    """A single (provider, model) callable endpoint."""

    def __init__(self, provider: str, model: str, cfg: dict) -> None:
        self.provider = provider
        self.model = model
        self.cfg = cfg

    @property
    def label(self) -> str:
        return f"{self.provider}/{self.model}"

    async def complete(self, prompt: str) -> str:
        kind = self.cfg["kind"]
        api_key = _require_api_key(self.cfg["key_env"])
        messages = [{"role": "user", "content": prompt}]

        if kind == "openai":
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": LLM_TEMPERATURE,
            }
            data = await _post_json(
                self.cfg["url"],
                payload,
                _bearer_headers(api_key, self.cfg.get("headers_extra")),
            )
            return _extract_openai_content(data, self.label)

        if kind == "gemini":
            url = f"{self.cfg['base_url']}/{self.model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": LLM_TEMPERATURE},
            }
            data = await _post_json(url, payload)
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError) as exc:
                raise ProviderError(f"Unexpected {self.label} response shape") from exc

        if kind == "hf_inference":
            url = f"{self.cfg['base_url']}/{self.model}"
            data = await _post_json(url, {"inputs": prompt}, _bearer_headers(api_key))
            if isinstance(data, list) and data:
                try:
                    return data[0]["generated_text"]
                except (KeyError, TypeError) as exc:
                    raise ProviderError(f"Unexpected {self.label} response shape") from exc
            raise ProviderError(f"Unexpected {self.label} response")

        raise ProviderError(f"Unknown wire protocol: {kind}")


def build_endpoints(chain: Optional[list[str]] = None) -> list[ModelEndpoint]:
    """Flatten the fallback chain into ordered (provider, model) endpoints."""
    endpoints: list[ModelEndpoint] = []
    for name in chain or LLM_FALLBACK_CHAIN:
        cfg = PROVIDERS.get(name)
        if cfg is None:
            logger.warning("Ignoring unknown provider in chain: %s", name)
            continue
        endpoints.extend(ModelEndpoint(name, model, cfg) for model in cfg["models"])
    return endpoints


ENDPOINTS: list[ModelEndpoint] = build_endpoints()

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


async def generate(prompt: str, provider_hint: Optional[str] = None) -> tuple[str, str]:
    """Generate a reply, returning ``(reply, "provider/model")``.

    Checks the TTL cache first, then tries every endpoint of every provider in
    the fallback chain (optionally starting at ``provider_hint``).
    Raises :class:`LLMUnavailableError` if all endpoints fail.
    """
    cache_key = _response_cache.make_key(prompt + "|" + (provider_hint or ""))
    cached = _response_cache.get(cache_key)
    if cached is not None:
        return cached[0], cached[1]

    endpoints = ENDPOINTS
    if provider_hint:
        hinted = [e for e in endpoints if e.provider == provider_hint]
        others = [e for e in endpoints if e.provider != provider_hint]
        endpoints = hinted + others

    errors: list[str] = []
    for endpoint in endpoints:
        try:
            reply = await _call_with_retry(endpoint.complete, prompt)
        except Exception as exc:  # noqa: BLE001 - collect and fall through
            logger.warning("Endpoint %s failed: %s", endpoint.label, exc)
            errors.append(f"{endpoint.label}: {exc}")
            continue
        _response_cache.set(cache_key, (reply, endpoint.label))
        return reply, endpoint.label

    raise LLMUnavailableError(errors)


def catalog() -> dict:
    """Public catalog of providers/models for API consumers and the UI."""
    return {
        provider: {
            "kind": cfg["kind"],
            "models": cfg["models"],
            "signup": cfg["signup"],
            "note": cfg["note"],
            "key_configured": bool(os.getenv(cfg["key_env"])),
        }
        for provider, cfg in PROVIDERS.items()
    }
