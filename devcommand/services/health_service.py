"""Server health-check service.

Monitors a list of HTTP(S) endpoints by issuing async GET requests
and recording response time and status code.  Uses ``urllib.request``
from the stdlib dispatched to an executor (no extra dependency).

For projects that need full async HTTP, swap the executor approach
for ``aiohttp`` or ``httpx``.
"""

from __future__ import annotations

import asyncio
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime

from devcommand.core.base_service import BaseService
from devcommand.models.health import (
    EndpointHealth,
    HealthStatus,
    ServerHealthSnapshot,
)
from devcommand.utils.cache import TTLCache

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT: float = 5.0  # seconds per request


class ServerHealthService(BaseService):
    """Async health-check service for monitored HTTP endpoints.

    Endpoints are supplied at construction time as a list of
    ``{"name": ..., "url": ...}`` dicts — typically sourced from
    the application config.

    Usage::

        endpoints = [
            {"name": "API", "url": "http://localhost:8000/health"},
            {"name": "Frontend", "url": "http://localhost:3000"},
        ]
        service = ServerHealthService(endpoints, cache_ttl=10.0)
        await service.start()
        snapshot = await service.check_all()
    """

    def __init__(
        self,
        endpoints: list[dict[str, str]] | None = None,
        cache_ttl: float = 10.0,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__()
        self._endpoints = endpoints or []
        self._timeout = timeout
        self._cache: TTLCache[ServerHealthSnapshot] = TTLCache(ttl=cache_ttl)

    async def start(self) -> None:
        await super().start()
        logger.info(
            "ServerHealthService started with %d endpoint(s)", len(self._endpoints)
        )

    async def stop(self) -> None:
        self._cache.clear()
        await super().stop()

    # -- public API ---------------------------------------------------------

    async def check_all(self) -> ServerHealthSnapshot:
        """Check every configured endpoint concurrently (cached)."""
        cached = self._cache.get("health")
        if cached is not None:
            return cached

        if not self._endpoints:
            return ServerHealthSnapshot()

        # Fan-out checks concurrently
        tasks = [self._check_one(ep) for ep in self._endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        endpoints: list[EndpointHealth] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                ep = self._endpoints[i]
                endpoints.append(
                    EndpointHealth(
                        name=ep.get("name", "unknown"),
                        url=ep.get("url", ""),
                        status=HealthStatus.UNHEALTHY,
                        error=str(result),
                    )
                )
            else:
                endpoints.append(result)  # type: ignore[arg-type]

        healthy = sum(1 for e in endpoints if e.status == HealthStatus.HEALTHY)
        snapshot = ServerHealthSnapshot(
            endpoints=endpoints,
            healthy_count=healthy,
            unhealthy_count=len(endpoints) - healthy,
            timestamp=datetime.now(),
        )
        self._cache.set("health", snapshot)
        return snapshot

    async def check_one(self, name: str) -> EndpointHealth | None:
        """Check a single endpoint by name."""
        for ep in self._endpoints:
            if ep.get("name") == name:
                return await self._check_one(ep)
        return None

    def add_endpoint(self, name: str, url: str) -> None:
        """Dynamically register a new endpoint."""
        self._endpoints.append({"name": name, "url": url})
        self._cache.invalidate("health")

    def remove_endpoint(self, name: str) -> None:
        """Remove an endpoint by name."""
        self._endpoints = [e for e in self._endpoints if e.get("name") != name]
        self._cache.invalidate("health")

    # -- private ------------------------------------------------------------

    async def _check_one(self, endpoint: dict[str, str]) -> EndpointHealth:
        """Check a single endpoint in the thread-pool executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._sync_check, endpoint
        )

    def _sync_check(self, endpoint: dict[str, str]) -> EndpointHealth:
        """Synchronous HTTP check — runs in executor."""
        name = endpoint.get("name", "unknown")
        url = endpoint.get("url", "")
        start = time.monotonic()

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status_code = resp.status
                elapsed = (time.monotonic() - start) * 1000

                if 200 <= status_code < 400:
                    health = HealthStatus.HEALTHY
                elif 400 <= status_code < 500:
                    health = HealthStatus.DEGRADED
                else:
                    health = HealthStatus.UNHEALTHY

                return EndpointHealth(
                    name=name,
                    url=url,
                    status=health,
                    status_code=status_code,
                    response_time_ms=round(elapsed, 2),
                )

        except urllib.error.HTTPError as exc:
            elapsed = (time.monotonic() - start) * 1000
            return EndpointHealth(
                name=name,
                url=url,
                status=HealthStatus.UNHEALTHY,
                status_code=exc.code,
                response_time_ms=round(elapsed, 2),
                error=str(exc.reason),
            )

        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return EndpointHealth(
                name=name,
                url=url,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(elapsed, 2),
                error=str(exc),
            )
