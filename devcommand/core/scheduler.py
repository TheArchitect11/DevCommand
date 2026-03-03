"""Central async scheduler for periodic service polling.

The :class:`ServiceScheduler` replaces the inline refresh loop in
``app.py`` with a production-grade scheduler that provides:

- Configurable tick interval
- Concurrent service invocation
- Per-service timeouts
- Slow-service detection and logging
- Exponential backoff on repeated failures
- Atomic state updates (all-or-nothing per tick)
- Non-blocking — runs as a single ``asyncio.Task``
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Type for a service job: async callable returning a dict snapshot
ServiceJob = Callable[[], Awaitable[dict[str, Any]]]

# Type for the callback that receives all results atomically
StateCallback = Callable[[dict[str, dict[str, Any]]], None]


@dataclass
class JobConfig:
    """Configuration for a single scheduled service job."""

    name: str
    fetch: ServiceJob
    enabled: bool = True
    timeout: float = 10.0           # seconds per invocation
    slow_threshold: float = 2.0     # warn if slower than this

    # Backoff state (managed internally)
    _consecutive_failures: int = field(default=0, init=False, repr=False)
    _backoff_until: float = field(default=0.0, init=False, repr=False)

    # Backoff parameters
    backoff_base: float = 2.0       # base multiplier
    backoff_max: float = 120.0      # ceiling in seconds
    backoff_reset_after: int = 1    # successes needed to reset

    def record_success(self) -> None:
        """Reset backoff state after a successful fetch."""
        if self._consecutive_failures > 0:
            logger.info(
                "Scheduler: %s recovered after %d failure(s)",
                self.name,
                self._consecutive_failures,
            )
        self._consecutive_failures = 0
        self._backoff_until = 0.0

    def record_failure(self) -> None:
        """Increase backoff delay after a failure."""
        self._consecutive_failures += 1
        delay = min(
            self.backoff_base ** self._consecutive_failures,
            self.backoff_max,
        )
        self._backoff_until = time.monotonic() + delay
        logger.warning(
            "Scheduler: %s failed (%d consecutive), backing off %.1fs",
            self.name,
            self._consecutive_failures,
            delay,
        )

    @property
    def is_backed_off(self) -> bool:
        """Whether this job is currently in a backoff window."""
        return time.monotonic() < self._backoff_until

    @property
    def backoff_remaining(self) -> float:
        """Seconds remaining in the backoff window (0 if not backed off)."""
        return max(0.0, self._backoff_until - time.monotonic())


class ServiceScheduler:
    """Central async scheduler that drives all service polling.

    Usage::

        scheduler = ServiceScheduler(
            interval=2.0,
            on_results=lambda results: print(results),
        )

        scheduler.register(JobConfig(
            name="system",
            fetch=system_service.get_snapshot_dict,
            timeout=5.0,
        ))

        await scheduler.start()   # spawns background task
        ...
        await scheduler.stop()    # cancels cleanly
    """

    def __init__(
        self,
        interval: float = 2.0,
        on_results: StateCallback | None = None,
    ) -> None:
        self._interval = interval
        self._on_results = on_results
        self._jobs: list[JobConfig] = []
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._tick_count = 0

    # -- registration -------------------------------------------------------

    def register(self, job: JobConfig) -> None:
        """Add a service job to the schedule."""
        self._jobs.append(job)
        logger.info(
            "Scheduler: registered job '%s' (timeout=%.1fs, slow_threshold=%.1fs)",
            job.name,
            job.timeout,
            job.slow_threshold,
        )

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Start the background tick loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="scheduler-loop")
        logger.info(
            "Scheduler started (interval=%.1fs, %d job(s))",
            self._interval,
            len(self._jobs),
        )

    async def stop(self) -> None:
        """Cancel the tick loop and wait for clean shutdown."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Scheduler stopped after %d tick(s)", self._tick_count)

    async def trigger(self) -> None:
        """Force an immediate tick (e.g. on manual refresh)."""
        await self._tick()

    # -- internals ----------------------------------------------------------

    async def _loop(self) -> None:
        """Main loop — sleeps, then ticks."""
        try:
            while self._running:
                await asyncio.sleep(self._interval)
                if self._running:
                    await self._tick()
        except asyncio.CancelledError:
            return

    async def _tick(self) -> None:
        """Execute all eligible jobs concurrently, then push results."""
        self._tick_count += 1
        tick_start = time.monotonic()

        # Filter to eligible jobs (enabled + not backed off)
        eligible = [j for j in self._jobs if j.enabled and not j.is_backed_off]
        skipped = len(self._jobs) - len(eligible)

        if skipped:
            backed_off_names = [
                f"{j.name}({j.backoff_remaining:.0f}s)"
                for j in self._jobs
                if j.is_backed_off
            ]
            logger.debug(
                "Scheduler tick #%d: %d eligible, %d skipped (backoff: %s)",
                self._tick_count,
                len(eligible),
                skipped,
                ", ".join(backed_off_names) or "none",
            )

        if not eligible:
            return

        # Fan-out all jobs concurrently with individual timeouts
        tasks = {
            job.name: asyncio.create_task(
                self._run_job(job), name=f"job-{job.name}"
            )
            for job in eligible
        }

        raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Collect successful results
        results: dict[str, dict[str, Any]] = {}
        for (name, _task), result in zip(tasks.items(), raw_results):
            if isinstance(result, Exception):
                logger.debug("Scheduler: job '%s' returned exception (already handled)", name)
            elif result is not None:
                results[name] = result

        # Atomic callback with all results
        if results and self._on_results is not None:
            try:
                self._on_results(results)
            except Exception:
                logger.exception("Scheduler: on_results callback failed")

        elapsed = (time.monotonic() - tick_start) * 1000
        logger.debug(
            "Scheduler tick #%d complete: %d/%d succeeded (%.0fms)",
            self._tick_count,
            len(results),
            len(eligible),
            elapsed,
        )

    async def _run_job(self, job: JobConfig) -> dict[str, Any] | None:
        """Execute a single job with timeout, timing, and backoff."""
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(job.fetch(), timeout=job.timeout)
            elapsed = time.monotonic() - start

            # Slow service warning
            if elapsed > job.slow_threshold:
                logger.warning(
                    "Scheduler: '%s' is slow (%.2fs > %.2fs threshold)",
                    job.name,
                    elapsed,
                    job.slow_threshold,
                )

            job.record_success()
            return result

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start
            logger.error(
                "Scheduler: '%s' timed out after %.1fs (limit=%.1fs)",
                job.name,
                elapsed,
                job.timeout,
            )
            job.record_failure()
            return None

        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Scheduler: '%s' failed after %.2fs — %s: %s",
                job.name,
                elapsed,
                type(exc).__name__,
                exc,
            )
            job.record_failure()
            return None

    # -- introspection ------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def jobs(self) -> list[JobConfig]:
        return list(self._jobs)
