"""TODO panel — task list with priority and status.

Subscribes to ``AppState.todo_data`` and renders a Rich table.
Makes **no** direct external calls.
"""

from __future__ import annotations

import logging
from typing import Any

from rich.table import Table
from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

logger = logging.getLogger(__name__)

_PRIORITY_STYLES: dict[str, str] = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "dim green",
}

_STATUS_ICONS: dict[str, str] = {
    "pending": "○",
    "in_progress": "◔",
    "done": "●",
    "cancelled": "✕",
}

_STATUS_STYLES: dict[str, str] = {
    "pending": "",
    "in_progress": "bold cyan",
    "done": "green",
    "cancelled": "dim strike",
}


class TodoPanel(Static):
    """Panel displaying the TODO task list."""

    todo_data: reactive[dict[str, Any]] = reactive({}, always_update=True)

    DEFAULT_CSS = """
    TodoPanel {
        height: 100%;
        overflow-y: auto;
    }
    """

    def render(self) -> Table | Text:
        data = self.todo_data
        if not data or not data.get("items"):
            return Text(
                "📋 No TODOs yet\n\n"
                "Items will appear here when\n"
                "added via the TODO service.",
                style="dim italic",
            )

        try:
            return self._build_table(data)
        except Exception:
            logger.exception("TodoPanel render error")
            return Text("⚠ Failed to render TODO data", style="bold red")

    def _build_table(self, data: dict[str, Any]) -> Table:
        items = data.get("items", [])
        pending = data.get("pending_count", 0)
        done = data.get("done_count", 0)
        total = data.get("total_count", 0)

        table = Table(
            title=f"📋 TODOs  [dim]({pending} pending / {done} done / {total} total)[/]",
            title_style="bold cyan",
            expand=True,
            show_edge=False,
            pad_edge=False,
        )
        table.add_column("", width=3)
        table.add_column("Title", ratio=4)
        table.add_column("Priority", width=10, justify="center")
        table.add_column("Status", width=12, justify="center")
        table.add_column("Tags", ratio=2)

        for item in items:
            status = item.get("status", "pending")
            priority = item.get("priority", "medium")

            icon = _STATUS_ICONS.get(status, "?")
            title_style = _STATUS_STYLES.get(status, "")
            prio_style = _PRIORITY_STYLES.get(priority, "")

            tags = ", ".join(item.get("tags", [])) or "—"
            title = item.get("title", "?")

            table.add_row(
                icon,
                Text(title, style=title_style),
                Text(priority.upper(), style=prio_style),
                Text(status.replace("_", " ").title(), style=title_style),
                Text(tags, style="dim"),
            )

        return table
