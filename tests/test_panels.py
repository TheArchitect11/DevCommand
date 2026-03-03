"""Tests for UI panels — rendering with data and fallback states."""

from __future__ import annotations

from devcommand.core.state import AppState
from devcommand.ui.panels.git_panel import GitPanel
from devcommand.ui.panels.docker_panel import DockerPanel
from devcommand.ui.panels.system_panel import SystemPanel
from devcommand.ui.panels.server_panel import ServerPanel
from devcommand.ui.panels.todo_panel import TodoPanel
from devcommand.ui.panels.logs_panel import LogsPanel

from rich.text import Text


def _make_panel(cls, state=None):
    """Create a panel and bind state."""
    p = cls(id=f"test-{cls.__name__}")
    p.bind_state(state or AppState())
    return p


class TestGitPanel:
    def test_empty_renders_text(self) -> None:
        p = _make_panel(GitPanel)
        assert isinstance(p.build_content(), Text)

    def test_with_data(self) -> None:
        state = AppState()
        state.push_git({"available": True, "branch": "main", "is_dirty": False,
                        "staged": [], "modified": ["a.py"], "recent_commits": [1, 2]})
        p = _make_panel(GitPanel, state)
        content = p.build_content()
        assert "main" in str(content)
        assert "Modified: 1" in str(content)


class TestDockerPanel:
    def test_empty_renders_text(self) -> None:
        p = _make_panel(DockerPanel)
        assert isinstance(p.build_content(), Text)

    def test_unavailable(self) -> None:
        state = AppState()
        state.push_docker({"available": False})
        p = _make_panel(DockerPanel, state)
        content = p.build_content()
        assert "unavailable" in str(content)


class TestSystemPanel:
    def test_empty_renders_text(self) -> None:
        p = _make_panel(SystemPanel)
        assert isinstance(p.build_content(), Text)

    def test_with_data(self) -> None:
        state = AppState()
        state.push_system({
            "cpu": {"percent": 42, "core_count": 8},
            "memory": {"percent": 50},
            "disk": {"percent": 60},
            "uptime_seconds": 7200,
        })
        p = _make_panel(SystemPanel, state)
        content = str(p.build_content())
        assert "42%" in content
        assert "2h 0m" in content


class TestServerPanel:
    def test_empty(self) -> None:
        p = _make_panel(ServerPanel)
        assert isinstance(p.build_content(), Text)


class TestTodoPanel:
    def test_empty(self) -> None:
        p = _make_panel(TodoPanel)
        assert isinstance(p.build_content(), Text)


class TestLogsPanel:
    def test_empty(self) -> None:
        p = _make_panel(LogsPanel)
        content = p.build_content()
        assert "No log" in str(content)

    def test_with_logs(self) -> None:
        state = AppState()
        state.push_log("Line 1")
        state.push_log("Line 2")
        p = _make_panel(LogsPanel, state)
        content = str(p.build_content())
        assert "Line 1" in content
        assert "Line 2" in content
