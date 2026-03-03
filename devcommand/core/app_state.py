"""Central reactive application state container.

``AppState`` holds all shared state for the TUI and exposes it via
Textual reactive attributes so that widgets automatically update when
values change.  Services write into the state; panels read from it.

The state stores **serialised dicts** (not Pydantic models) in each
reactive field.  This avoids Textual's comparison pitfalls with complex
objects and lets panels deserialise only when they need to render.
"""

from __future__ import annotations

import logging
from typing import Any

from textual.reactive import reactive
from textual.widget import Widget

logger = logging.getLogger(__name__)

# Type alias — each snapshot is stored as a plain dict for safe reactivity
SnapshotDict = dict[str, Any]


class AppState(Widget):
    """Invisible widget acting as the single source of truth.

    **Convention**: services call one of the ``push_*`` methods after
    every refresh tick.  Panels ``watch`` the matching reactive
    attribute and re-render when it changes.
    """

    # -- Reactive snapshot stores -------------------------------------------
    # Each stores the dict form of the corresponding Pydantic snapshot.
    # Using ``always_update=True`` ensures watchers fire even when the
    # dict contents are identical (important for timestamp-bearing data).

    system_data: reactive[SnapshotDict] = reactive({}, always_update=True)
    docker_data: reactive[SnapshotDict] = reactive({}, always_update=True)
    git_data: reactive[SnapshotDict] = reactive({}, always_update=True)
    health_data: reactive[SnapshotDict] = reactive({}, always_update=True)
    todo_data: reactive[SnapshotDict] = reactive({}, always_update=True)

    last_error: reactive[str] = reactive("")

    # -----------------------------------------------------------------------

    DEFAULT_CSS = """
    AppState { display: none; }
    """

    # -- Push helpers (called by services / refresh loop) --------------------

    def push_system(self, data: SnapshotDict) -> None:
        """Replace the system snapshot."""
        self.system_data = data

    def push_docker(self, data: SnapshotDict) -> None:
        """Replace the Docker snapshot."""
        self.docker_data = data

    def push_git(self, data: SnapshotDict) -> None:
        """Replace the Git snapshot."""
        self.git_data = data

    def push_health(self, data: SnapshotDict) -> None:
        """Replace the server-health snapshot."""
        self.health_data = data

    def push_todo(self, data: SnapshotDict) -> None:
        """Replace the TODO snapshot."""
        self.todo_data = data

    def record_error(self, error: str) -> None:
        """Store the latest error for UI display."""
        self.last_error = error
        logger.error("AppState recorded error: %s", error)
