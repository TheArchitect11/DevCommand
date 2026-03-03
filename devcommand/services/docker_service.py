"""Docker service for inspecting containers and images.

All Docker SDK calls are dispatched to a thread-pool executor to avoid
blocking the asyncio event loop.  Results are cached via
:class:`~devcommand.utils.cache.TTLCache`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from devcommand.core.base_service import BaseService
from devcommand.models.docker import (
    ContainerInfo,
    ContainerStatus,
    DockerSnapshot,
    ImageInfo,
)
from devcommand.utils.cache import TTLCache

logger = logging.getLogger(__name__)


class DockerService(BaseService):
    """Async Docker service.

    Gracefully degrades when the Docker daemon is unavailable —
    all public methods return empty/safe defaults instead of raising.

    Usage::

        service = DockerService(cache_ttl=5.0)
        await service.start()
        snapshot = await service.get_snapshot()
    """

    def __init__(self, cache_ttl: float = 5.0) -> None:
        super().__init__()
        self._cache: TTLCache[DockerSnapshot] = TTLCache(ttl=cache_ttl)
        self._client: Any = None  # docker.DockerClient | None

    async def start(self) -> None:
        """Connect to the Docker daemon (best-effort)."""
        await super().start()
        loop = asyncio.get_running_loop()
        try:
            import docker

            self._client = await loop.run_in_executor(None, docker.from_env)
            logger.info("Connected to Docker daemon")
        except Exception:
            logger.warning("Docker daemon is not available", exc_info=True)
            self._client = None

    async def stop(self) -> None:
        """Close the Docker client and clear cache."""
        if self._client is not None:
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, self._client.close)
            except Exception:
                logger.debug("Error closing Docker client", exc_info=True)
        self._cache.clear()
        await super().stop()

    # -- public API ---------------------------------------------------------

    async def get_snapshot(self) -> DockerSnapshot:
        """Return aggregated Docker state (cached)."""
        cached = self._cache.get("snapshot")
        if cached is not None:
            return cached

        if self._client is None:
            return DockerSnapshot(available=False)

        loop = asyncio.get_running_loop()
        try:
            snapshot = await loop.run_in_executor(None, self._collect_snapshot)
        except Exception:
            logger.exception("Error collecting Docker snapshot")
            return DockerSnapshot(available=False)

        self._cache.set("snapshot", snapshot)
        return snapshot

    async def get_containers(self, all_: bool = False) -> list[ContainerInfo]:
        """Return container list."""
        snapshot = await self.get_snapshot()
        if all_:
            return snapshot.containers
        return [c for c in snapshot.containers if c.status == ContainerStatus.RUNNING]

    async def get_images(self) -> list[ImageInfo]:
        """Return image list."""
        snapshot = await self.get_snapshot()
        return snapshot.images

    @property
    def is_available(self) -> bool:
        """Whether the Docker daemon connection is live."""
        return self._client is not None

    # -- private (sync, runs in executor) -----------------------------------

    def _collect_snapshot(self) -> DockerSnapshot:
        """Synchronous Docker data collection."""
        client = self._client
        containers_raw = client.containers.list(all=True)
        images_raw = client.images.list()

        containers: list[ContainerInfo] = []
        running = 0
        stopped = 0
        for c in containers_raw:
            status = self._parse_status(c.status)
            if status == ContainerStatus.RUNNING:
                running += 1
            else:
                stopped += 1

            # Port extraction — best effort
            ports: dict[str, str | None] = {}
            try:
                for k, v in (c.ports or {}).items():
                    ports[str(k)] = v[0]["HostPort"] if v else None
            except (KeyError, IndexError, TypeError):
                pass

            containers.append(
                ContainerInfo(
                    id=c.short_id,
                    name=c.name,
                    status=status,
                    image=str(c.image.tags[0]) if c.image.tags else "unknown",
                    ports=ports,
                )
            )

        images: list[ImageInfo] = [
            ImageInfo(
                id=img.short_id,
                tags=img.tags or [],
                size_bytes=img.attrs.get("Size", 0),
            )
            for img in images_raw
        ]

        return DockerSnapshot(
            available=True,
            containers=containers,
            images=images,
            running_count=running,
            stopped_count=stopped,
            total_count=len(containers),
            timestamp=datetime.now(),
        )

    @staticmethod
    def _parse_status(raw: str) -> ContainerStatus:
        """Normalize Docker status string to enum."""
        try:
            return ContainerStatus(raw.lower())
        except ValueError:
            return ContainerStatus.UNKNOWN
