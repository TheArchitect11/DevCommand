"""Base panel mixin for DevCommand TUI panels.

Every panel inherits from :class:`BasePanel` which provides:

- A reference to :class:`~devcommand.core.state.AppState`
- A ``refresh_content`` hook called by the app on each tick
- Built-in error isolation (exceptions rendered inside the panel)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.text import Text
from textual.widgets import Static

if TYPE_CHECKING:
    from devcommand.core.state import AppState

logger = logging.getLogger(__name__)


class BasePanel(Static):
    """Abstract base for all TUI panels.

    Subclasses override :meth:`build_content` to return a Rich
    renderable.  :meth:`refresh_content` drives the update cycle
    and wraps ``build_content`` in an error boundary.
    """

    # Set by the app after composition
    _state: AppState | None = None

    @property
    def state(self) -> AppState:
        """Access central state (set by the app on mount)."""
        assert self._state is not None, "State not bound — call bind_state() first"
        return self._state

    def bind_state(self, state: AppState) -> None:
        """Bind the shared state to this panel."""
        self._state = state

    def refresh_content(self) -> None:
        """Pull data from state and re-render.

        Error isolation: any exception in ``build_content()`` is
        caught and rendered as an error message inside the panel.
        Safely does nothing if called outside a running Textual app.
        """
        try:
            content = self.build_content()
            self.update(content)
        except Exception as exc:
            logger.exception("Panel %s render error", self.id)
            import contextlib
            with contextlib.suppress(Exception):
                self.update(Text(f"⚠ Error: {exc}", style="bold red"))

    def build_content(self) -> Text:
        """Override in subclass to return a Rich renderable.

        Default implementation returns a placeholder.
        """
        return Text("⏳ Loading…", style="dim")
