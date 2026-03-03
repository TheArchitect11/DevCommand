"""Performance profiling hooks for DevCommand.

Provides lightweight instrumentation that can be toggled on/off
via config.  Designed for Apple Silicon (M3) — avoids heavy
profiling frameworks and uses ``time.perf_counter_ns()`` for
nanosecond precision with minimal overhead.

Usage::

    from devcommand.utils.profiling import profiler, timed

    @timed("service.system.get_snapshot")
    async def get_snapshot() -> SystemSnapshot:
        ...

    # Or manual context manager:
    with profiler.measure("scheduler.tick"):
        await tick()

    profiler.report()  # dump summary to logger
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class _TimingSample:
    """Aggregated timing for a single named operation."""

    count: int = 0
    total_ns: int = 0
    min_ns: int = 0
    max_ns: int = 0

    def record(self, ns: int) -> None:
        self.count += 1
        self.total_ns += ns
        if self.count == 1:
            self.min_ns = ns
            self.max_ns = ns
        else:
            self.min_ns = min(self.min_ns, ns)
            self.max_ns = max(self.max_ns, ns)

    @property
    def avg_ms(self) -> float:
        return (self.total_ns / self.count / 1_000_000) if self.count else 0.0

    @property
    def min_ms(self) -> float:
        return self.min_ns / 1_000_000

    @property
    def max_ms(self) -> float:
        return self.max_ns / 1_000_000

    @property
    def total_ms(self) -> float:
        return self.total_ns / 1_000_000


class Profiler:
    """Global performance profiler with nanosecond precision.

    Thread-safe for the single-threaded asyncio loop.
    Uses ``time.perf_counter_ns()`` — the highest resolution
    monotonic clock available.
    """

    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled
        self._samples: dict[str, _TimingSample] = defaultdict(_TimingSample)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @contextmanager
    def measure(self, name: str) -> Generator[None, None, None]:
        """Context manager that records wall-clock time for *name*."""
        if not self._enabled:
            yield
            return
        start = time.perf_counter_ns()
        try:
            yield
        finally:
            elapsed = time.perf_counter_ns() - start
            self._samples[name].record(elapsed)

    def record(self, name: str, duration_ns: int) -> None:
        """Manually record a timing sample."""
        if self._enabled:
            self._samples[name].record(duration_ns)

    def report(self) -> dict[str, dict[str, float]]:
        """Dump profiling summary and log it.

        Returns a dict of ``{name: {count, avg_ms, min_ms, max_ms, total_ms}}``.
        """
        report: dict[str, dict[str, float]] = {}
        for name, sample in sorted(self._samples.items()):
            report[name] = {
                "count": sample.count,
                "avg_ms": round(sample.avg_ms, 3),
                "min_ms": round(sample.min_ms, 3),
                "max_ms": round(sample.max_ms, 3),
                "total_ms": round(sample.total_ms, 3),
            }
            logger.info(
                "PROFILE %-40s  count=%d  avg=%.3fms  min=%.3fms  max=%.3fms  total=%.3fms",
                name,
                sample.count,
                sample.avg_ms,
                sample.min_ms,
                sample.max_ms,
                sample.total_ms,
            )
        return report

    def reset(self) -> None:
        """Clear all collected samples."""
        self._samples.clear()


# Module-level singleton
profiler = Profiler(enabled=False)


def timed(name: str) -> Any:
    """Decorator that profiles an async or sync function.

    Usage::

        @timed("service.system.refresh")
        async def refresh(): ...
    """
    def decorator(fn: Any) -> Any:
        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with profiler.measure(name):
                    return await fn(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with profiler.measure(name):
                    return fn(*args, **kwargs)
            return sync_wrapper
    return decorator
