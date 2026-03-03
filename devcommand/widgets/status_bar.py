"""Reusable status bar widget."""

from __future__ import annotations

from typing import Any

from textual.widgets import Static


class StatusBar(Static):
    """A configurable status bar widget.

    Displays a single line of contextual information that can be
    updated reactively from service events.
    """

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(self, text: str = "Ready", **kwargs: Any) -> None:
        super().__init__(text, **kwargs)

    def update_status(self, text: str) -> None:
        """Update the displayed status text."""
        self.update(text)
