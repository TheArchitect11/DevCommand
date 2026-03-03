"""Logs panel — displays recent log messages.

Connects to Python :mod:`logging` via a custom handler that pushes
messages into :class:`~devcommand.core.state.AppState`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.text import Text

from devcommand.ui.panels.base import BasePanel

if TYPE_CHECKING:
    from devcommand.core.state import AppState

logger = logging.getLogger(__name__)


class StateLogHandler(logging.Handler):
    """Logging handler that writes formatted messages into AppState.logs.

    Installed once at app startup so every log record is captured
    for display in the LogsPanel.
    """

    def __init__(self, state: AppState, max_lines: int = 200) -> None:
        super().__init__()
        self._state = state
        self._max = max_lines
        self.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._state.push_log(msg)
        except Exception:
            self.handleError(record)


class LogsPanel(BasePanel):
    """Scrollable panel displaying the last N log messages."""

    def build_content(self) -> Text:
        logs = self.state.logs
        if not logs:
            return Text("📝 No log messages yet", style="dim")

        # Show last 30 lines (panel height limited)
        recent = logs[-30:]
        return Text("\n".join(recent), style="white")
