"""Tests for core/state.py — AppState dataclass."""

from __future__ import annotations

from devcommand.core.state import AppState


class TestAppState:
    def test_defaults(self) -> None:
        s = AppState()
        assert s.git_state == {}
        assert s.docker_state == {}
        assert s.system_state == {}
        assert s.todo_state == {}
        assert s.server_state == {}
        assert s.logs == []
        assert s.tick_count == 0

    def test_push_methods(self) -> None:
        s = AppState()
        s.push_git({"branch": "main"})
        assert s.git_state["branch"] == "main"
        s.push_docker({"available": True})
        assert s.docker_state["available"] is True
        s.push_system({"cpu": {}})
        assert "cpu" in s.system_state

    def test_log_capped(self) -> None:
        s = AppState()
        for i in range(250):
            s.push_log(f"line {i}")
        assert len(s.logs) == 200
        assert s.logs[-1] == "line 249"

    def test_increment_tick(self) -> None:
        s = AppState()
        s.increment_tick()
        s.increment_tick()
        assert s.tick_count == 2

    def test_record_error(self) -> None:
        s = AppState()
        s.record_error("boom")
        assert s.last_error == "boom"
