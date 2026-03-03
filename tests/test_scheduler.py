"""Tests for the central async scheduler."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from devcommand.core.scheduler import JobConfig, ServiceScheduler


class TestJobConfig:
    """Tests for JobConfig backoff logic."""

    def test_initial_state(self) -> None:
        job = JobConfig(name="test", fetch=lambda: None)  # type: ignore
        assert not job.is_backed_off
        assert job._consecutive_failures == 0

    def test_backoff_on_failure(self) -> None:
        job = JobConfig(name="test", fetch=lambda: None, backoff_base=2.0)  # type: ignore
        job.record_failure()
        assert job._consecutive_failures == 1
        assert job.is_backed_off
        assert job.backoff_remaining > 0

    def test_backoff_escalation(self) -> None:
        job = JobConfig(name="test", fetch=lambda: None, backoff_base=2.0)  # type: ignore
        job.record_failure()
        r1 = job.backoff_remaining
        job.record_failure()
        r2 = job.backoff_remaining
        assert r2 > r1  # second backoff longer

    def test_backoff_capped(self) -> None:
        job = JobConfig(
            name="test", fetch=lambda: None,  # type: ignore
            backoff_base=2.0, backoff_max=5.0,
        )
        for _ in range(20):
            job.record_failure()
        assert job.backoff_remaining <= 5.0 + 0.1  # small tolerance

    def test_reset_on_success(self) -> None:
        job = JobConfig(name="test", fetch=lambda: None)  # type: ignore
        job.record_failure()
        job.record_failure()
        job.record_success()
        assert job._consecutive_failures == 0
        assert not job.is_backed_off


class TestServiceScheduler:
    """Tests for ServiceScheduler."""

    @pytest.mark.asyncio
    async def test_trigger_collects_results(self) -> None:
        results: list[dict[str, dict[str, Any]]] = []

        async def fast() -> dict[str, Any]:
            return {"val": 1}

        sched = ServiceScheduler(interval=1.0, on_results=results.append)
        sched.register(JobConfig(name="fast", fetch=fast, timeout=1.0))
        await sched.trigger()

        assert len(results) == 1
        assert "fast" in results[0]

    @pytest.mark.asyncio
    async def test_failed_jobs_excluded(self) -> None:
        results: list[dict[str, dict[str, Any]]] = []

        async def fail() -> dict[str, Any]:
            raise RuntimeError("boom")

        async def ok() -> dict[str, Any]:
            return {"ok": True}

        sched = ServiceScheduler(interval=1.0, on_results=results.append)
        sched.register(JobConfig(name="ok", fetch=ok, timeout=1.0))
        sched.register(JobConfig(name="fail", fetch=fail, timeout=1.0))
        await sched.trigger()

        assert "ok" in results[0]
        assert "fail" not in results[0]

    @pytest.mark.asyncio
    async def test_timeout_triggers_backoff(self) -> None:
        async def slow() -> dict[str, Any]:
            await asyncio.sleep(10)
            return {}

        sched = ServiceScheduler(interval=1.0)
        job = JobConfig(name="slow", fetch=slow, timeout=0.05)
        sched.register(job)
        await sched.trigger()

        assert job._consecutive_failures == 1
        assert job.is_backed_off

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self) -> None:
        sched = ServiceScheduler(interval=0.05)

        async def noop() -> dict[str, Any]:
            return {}

        sched.register(JobConfig(name="noop", fetch=noop, timeout=1.0))
        await sched.start()
        await asyncio.sleep(0.2)
        await sched.stop()

        assert sched.tick_count >= 2
        assert not sched.is_running

    @pytest.mark.asyncio
    async def test_disabled_job_skipped(self) -> None:
        results: list[dict[str, dict[str, Any]]] = []

        async def fetch() -> dict[str, Any]:
            return {"val": 1}

        sched = ServiceScheduler(interval=1.0, on_results=results.append)
        sched.register(JobConfig(name="disabled", fetch=fetch, enabled=False))
        await sched.trigger()

        assert len(results) == 0  # no results because only job was disabled
