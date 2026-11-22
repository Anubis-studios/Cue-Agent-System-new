"""Small TTL cache for LLM responses."""

import hashlib
import time
from typing import Any, Optional


class TTLCache:
    """In-memory key/value cache with per-entry time-to-live expiry."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    @staticmethod
    def make_key(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        created_at, value = entry
        if time.monotonic() - created_at >= self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic(), value)
