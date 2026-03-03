"""Central application state — single source of truth.

All panel data flows through :class:`AppState`.  Services push
data in; panels read it out.  No panel should ever call external
logic directly.

The state is a plain dataclass (not a Textual widget) so it can be
used in tests without a running app.  The app holds one instance and
passes it to panels on composition.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Snapshot dict — each domain's data as a plain dict
SnapshotDict = dict[str, Any]


@dataclass
class AppState:
    """Centralised, mutable state container.

    Fields default to empty dicts so panels always have something
    safe to read.  The scheduler replaces these atomically on each
    tick.
    """

    git_state: SnapshotDict = field(default_factory=dict)
    docker_state: SnapshotDict = field(default_factory=dict)
    system_state: SnapshotDict = field(default_factory=dict)
    todo_state: SnapshotDict = field(default_factory=dict)
    server_state: SnapshotDict = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)

    last_error: str = ""
    tick_count: int = 0

    # -- push helpers -------------------------------------------------------

    def push_git(self, data: SnapshotDict) -> None:
        self.git_state = data

    def push_docker(self, data: SnapshotDict) -> None:
        self.docker_state = data

    def push_system(self, data: SnapshotDict) -> None:
        self.system_state = data

    def push_todo(self, data: SnapshotDict) -> None:
        self.todo_state = data

    def push_server(self, data: SnapshotDict) -> None:
        self.server_state = data

    def push_log(self, message: str) -> None:
        """Append a log message (capped at 200 lines)."""
        self.logs.append(message)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]

    def record_error(self, error: str) -> None:
        self.last_error = error
        logger.error("AppState recorded error: %s", error)

    def increment_tick(self) -> None:
        self.tick_count += 1
