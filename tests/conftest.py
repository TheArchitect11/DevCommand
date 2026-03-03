"""Shared test fixtures for DevCommand."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from devcommand.config.settings import AppSettings
from devcommand.core.event_bus import EventBus
from devcommand.core.scheduler import JobConfig, ServiceScheduler

# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app_settings() -> AppSettings:
    """Default AppSettings for testing."""
    return AppSettings()


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


# ---------------------------------------------------------------------------
# Service mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_system_service() -> MagicMock:
    svc = MagicMock()
    svc.start = AsyncMock()
    svc.stop = AsyncMock()
    svc.get_snapshot = AsyncMock(return_value=MagicMock(
        model_dump=MagicMock(return_value={
            "cpu": {"percent": 25.0, "core_count": 8, "frequency_mhz": 3200},
            "memory": {"total": 16_000_000_000, "used": 8_000_000_000,
                       "available": 8_000_000_000, "percent": 50.0},
            "disk": {"total": 500_000_000_000, "used": 250_000_000_000,
                     "free": 250_000_000_000, "percent": 50.0},
            "network": {"bytes_sent": 1000, "bytes_recv": 2000,
                        "packets_sent": 10, "packets_recv": 20},
            "uptime_seconds": 86400,
            "top_processes": [],
        })
    ))
    svc._cache = MagicMock()
    return svc


@pytest.fixture
def mock_docker_service() -> MagicMock:
    svc = MagicMock()
    svc.start = AsyncMock()
    svc.stop = AsyncMock()
    svc.get_snapshot = AsyncMock(return_value=MagicMock(
        model_dump=MagicMock(return_value={"available": True, "containers": [], "images": []})
    ))
    svc._cache = MagicMock()
    return svc


@pytest.fixture
def mock_git_service() -> MagicMock:
    svc = MagicMock()
    svc.start = AsyncMock()
    svc.stop = AsyncMock()
    svc.get_status = AsyncMock(return_value=MagicMock(
        model_dump=MagicMock(return_value={
            "available": True, "branch": "main", "is_dirty": False,
            "staged": [], "modified": [], "untracked": [],
            "recent_commits": [], "stash_count": 0,
        })
    ))
    svc._cache = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# Scheduler fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scheduler() -> ServiceScheduler:
    return ServiceScheduler(interval=0.1)


def make_job(name: str = "test", result: dict[str, Any] | None = None) -> JobConfig:
    """Create a test JobConfig with a fast mock fetch."""
    async def _fetch() -> dict[str, Any]:
        return result or {"ok": True}

    return JobConfig(name=name, fetch=_fetch, timeout=1.0)
