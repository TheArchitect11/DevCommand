"""System metrics service using psutil.

Collects CPU, memory, disk, network, and top-process metrics via
``psutil``.  All blocking psutil calls run in a thread-pool executor.
Results are cached with :class:`~devcommand.utils.cache.TTLCache`
to avoid redundant syscalls within the same refresh cycle.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime

import psutil

from devcommand.core.base_service import BaseService
from devcommand.models.system import (
    CpuMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessInfo,
    SystemSnapshot,
)
from devcommand.utils.cache import TTLCache

logger = logging.getLogger(__name__)

_BOOT_TIME: float = psutil.boot_time()


class SystemService(BaseService):
    """Async system-metrics service backed by psutil.

    Usage::

        service = SystemService(cache_ttl=2.0)
        await service.start()
        snapshot = await service.get_snapshot()
    """

    def __init__(self, cache_ttl: float = 2.0, top_n_processes: int = 5) -> None:
        super().__init__()
        self._cache: TTLCache[SystemSnapshot] = TTLCache(ttl=cache_ttl)
        self._top_n = top_n_processes

    async def start(self) -> None:
        """Start the service (no persistent resources needed)."""
        await super().start()
        # Prime cpu_percent so first real read isn't always 0
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=None))

    async def stop(self) -> None:
        """Stop the service and clear the cache."""
        self._cache.clear()
        await super().stop()

    # -- public API ---------------------------------------------------------

    async def get_snapshot(self) -> SystemSnapshot:
        """Return aggregated system metrics (cached)."""
        cached = self._cache.get("snapshot")
        if cached is not None:
            return cached

        loop = asyncio.get_running_loop()
        snapshot = await loop.run_in_executor(None, self._collect_snapshot)
        self._cache.set("snapshot", snapshot)
        return snapshot

    async def get_cpu(self) -> CpuMetrics:
        """Return only CPU metrics."""
        snapshot = await self.get_snapshot()
        return snapshot.cpu

    async def get_memory(self) -> MemoryMetrics:
        """Return only memory metrics."""
        snapshot = await self.get_snapshot()
        return snapshot.memory

    # -- private (sync, runs in executor) -----------------------------------

    def _collect_snapshot(self) -> SystemSnapshot:
        """Synchronous metric collection."""
        cpu_freq = psutil.cpu_freq()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        # Top processes by CPU — best-effort, skip permission errors
        procs: list[ProcessInfo] = []
        try:
            attrs = ["pid", "name", "cpu_percent", "memory_percent", "status"]
            for p in psutil.process_iter(attrs):
                info = p.info
                procs.append(
                    ProcessInfo(
                        pid=info["pid"],
                        name=info["name"] or "unknown",
                        cpu_percent=info.get("cpu_percent") or 0.0,
                        memory_percent=info.get("memory_percent") or 0.0,
                        status=info.get("status") or "running",
                    )
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        procs.sort(key=lambda p: p.cpu_percent, reverse=True)

        return SystemSnapshot(
            cpu=CpuMetrics(
                percent=psutil.cpu_percent(interval=None),
                core_count=psutil.cpu_count(logical=True) or 1,
                frequency_mhz=cpu_freq.current if cpu_freq else None,
            ),
            memory=MemoryMetrics(
                total=mem.total,
                used=mem.used,
                available=mem.available,
                percent=mem.percent,
            ),
            disk=DiskMetrics(
                total=disk.total,
                used=disk.used,
                free=disk.free,
                percent=disk.percent,
            ),
            network=NetworkMetrics(
                bytes_sent=net.bytes_sent,
                bytes_recv=net.bytes_recv,
                packets_sent=net.packets_sent,
                packets_recv=net.packets_recv,
            ),
            top_processes=procs[: self._top_n],
            timestamp=datetime.now(),
            uptime_seconds=time.time() - _BOOT_TIME,
        )
