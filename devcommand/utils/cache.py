"""Async-aware TTL cache for reducing expensive service calls.

Provides a generic :class:`TTLCache` that stores results keyed by
arbitrary strings and expires them after a configurable TTL.  Designed
to be embedded inside individual services so each controls its own
cache lifetime independently.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class _CacheEntry(Generic[T]):
    """Internal wrapper holding a cached value and its expiry timestamp."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: T, ttl: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl


class TTLCache(Generic[T]):
    """A simple, thread-safe, TTL-based in-memory cache.

    Each service instantiates its own ``TTLCache`` so that cache
    lifetimes can be tuned independently.

    Example::

        cache: TTLCache[SystemSnapshot] = TTLCache(ttl=2.0)

        async def get_metrics() -> SystemSnapshot:
            cached = cache.get("snapshot")
            if cached is not None:
                return cached
            snapshot = await _expensive_call()
            cache.set("snapshot", snapshot)
            return snapshot
    """

    def __init__(self, ttl: float = 5.0, max_size: int = 128) -> None:
        self._ttl = ttl
        self._max_size = max_size
        self._store: dict[str, _CacheEntry[T]] = {}
        self._lock = asyncio.Lock()

    @property
    def ttl(self) -> float:
        """Current TTL in seconds."""
        return self._ttl

    def get(self, key: str) -> T | None:
        """Return cached value if present and not expired, else ``None``."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        """Store *value* under *key* with the configured TTL."""
        # Evict oldest if at capacity
        if len(self._store) >= self._max_size and key not in self._store:
            oldest = next(iter(self._store))
            del self._store[oldest]
        self._store[key] = _CacheEntry(value, self._ttl)

    def invalidate(self, key: str) -> None:
        """Explicitly remove a cached entry."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Drop all cached entries."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None
