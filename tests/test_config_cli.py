"""Tests for config, CLI, logging, and profiling utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from devcommand.cli import parse_args
from devcommand.config.settings import AppSettings, PluginSettings, SchedulerSettings
from devcommand.config.themes import available_themes, get_theme
from devcommand.utils.profiling import Profiler, timed

# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestAppSettings:
    def test_defaults(self) -> None:
        s = AppSettings()
        assert s.ui.refresh_interval == 1.0
        assert s.scheduler.tick_interval == 2.0
        assert s.plugins.enabled is True

    def test_scheduler_bounds(self) -> None:
        with pytest.raises(ValueError):
            SchedulerSettings(tick_interval=0.1)  # below ge=0.5

    def test_plugin_disabled_list(self) -> None:
        s = AppSettings(plugins=PluginSettings(disabled=["foo", "bar"]))
        assert "foo" in s.plugins.disabled


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    def test_defaults(self) -> None:
        args = parse_args([])
        assert args.workspace == Path.cwd()
        assert args.refresh is None
        assert args.debug is False
        assert args.no_plugins is False
        assert args.profile is False

    def test_flags(self) -> None:
        args = parse_args(["--debug", "--profile", "--no-plugins", "-r", "5.0"])
        assert args.debug is True
        assert args.profile is True
        assert args.no_plugins is True
        assert args.refresh == 5.0

    def test_workspace(self, tmp_path: Path) -> None:
        args = parse_args(["-w", str(tmp_path)])
        assert args.workspace == tmp_path.resolve()


# ---------------------------------------------------------------------------
# Theme tests
# ---------------------------------------------------------------------------

class TestThemes:
    def test_available_themes(self) -> None:
        themes = available_themes()
        assert "dark" in themes
        assert "light" in themes
        assert len(themes) >= 5

    def test_get_theme_fallback(self) -> None:
        theme = get_theme("nonexistent")
        assert theme == get_theme("dark")

    def test_theme_keys(self) -> None:
        for name in available_themes():
            theme = get_theme(name)
            assert "primary" in theme
            assert "background" in theme
            assert "text" in theme


# ---------------------------------------------------------------------------
# Profiling tests
# ---------------------------------------------------------------------------

class TestProfiler:
    def test_disabled_noop(self) -> None:
        p = Profiler(enabled=False)
        with p.measure("test"):
            pass
        report = p.report()
        assert len(report) == 0

    def test_enabled_records(self) -> None:
        p = Profiler(enabled=True)
        with p.measure("test"):
            _ = sum(range(100))
        report = p.report()
        assert "test" in report
        assert report["test"]["count"] == 1
        assert report["test"]["avg_ms"] >= 0

    def test_reset(self) -> None:
        p = Profiler(enabled=True)
        p.record("x", 1_000_000)
        p.reset()
        assert len(p.report()) == 0


class TestTimedDecorator:
    @pytest.mark.asyncio
    async def test_async_timed(self) -> None:
        from devcommand.utils.profiling import profiler
        profiler.enabled = True
        profiler.reset()

        @timed("test.async_fn")
        async def _fn() -> int:
            return 42

        result = await _fn()
        assert result == 42

        report = profiler.report()
        assert "test.async_fn" in report
        profiler.enabled = False


# ---------------------------------------------------------------------------
# Structured logging tests
# ---------------------------------------------------------------------------

class TestStructuredLogging:
    def test_json_formatter(self) -> None:
        from devcommand.utils.logging import StructuredFormatter

        fmt = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello %s", args=("world",), exc_info=None,
        )
        output = fmt.format(record)
        parsed = json.loads(output)
        assert parsed["msg"] == "hello world"
        assert parsed["level"] == "INFO"
        assert "ts" in parsed
        assert "pid" in parsed
