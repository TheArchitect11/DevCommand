"""Server health panel — endpoint status table.

Subscribes to ``AppState.health_data`` and renders a Rich table.
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

_STATUS_STYLES: dict[str, str] = {
    "healthy": "bold green",
    "degraded": "yellow",
    "unhealthy": "bold red",
    "unknown": "dim",
}

_STATUS_ICONS: dict[str, str] = {
    "healthy": "🟢",
    "degraded": "🟡",
    "unhealthy": "🔴",
    "unknown": "⚪",
}


class ServerPanel(Static):
    """Panel displaying server / endpoint health checks."""

    health_data: reactive[dict[str, Any]] = reactive({}, always_update=True)

    DEFAULT_CSS = """
    ServerPanel {
        height: 100%;
        overflow-y: auto;
    }
    """

    def render(self) -> Table | Text:
        data = self.health_data
        if not data:
            return Text(
                "🌐 No health endpoints configured\n\n"
                "Add endpoints to `.devcommand.yml`\n"
                "under the `health.endpoints` key.",
                style="dim italic",
            )

        try:
            return self._build_table(data)
        except Exception:
            logger.exception("ServerPanel render error")
            return Text("⚠ Failed to render health data", style="bold red")

    def _build_table(self, data: dict[str, Any]) -> Table:
        endpoints = data.get("endpoints", [])
        healthy = data.get("healthy_count", 0)
        total = len(endpoints)

        table = Table(
            title=f"🌐 Server Health  [dim]({healthy}/{total} healthy)[/]",
            title_style="bold cyan",
            expand=True,
            show_edge=False,
            pad_edge=False,
        )
        table.add_column("", width=3)
        table.add_column("Name", style="bold", ratio=2)
        table.add_column("URL", style="dim", ratio=3)
        table.add_column("Code", width=5, justify="center")
        table.add_column("Time", width=8, justify="right")
        table.add_column("Error", ratio=2)

        if not endpoints:
            table.add_row("", "—", "No endpoints configured", "", "", "")
        else:
            for ep in endpoints:
                status = ep.get("status", "unknown")
                icon = _STATUS_ICONS.get(status, "⚪")
                style = _STATUS_STYLES.get(status, "")

                code = ep.get("status_code")
                code_str = str(code) if code is not None else "—"

                rt = ep.get("response_time_ms")
                time_str = f"{rt:.0f}ms" if rt is not None else "—"

                error = ep.get("error") or ""
                if len(error) > 30:
                    error = error[:27] + "…"

                table.add_row(
                    icon,
                    Text(ep.get("name", "?"), style=style),
                    ep.get("url", "?"),
                    code_str,
                    time_str,
                    Text(error, style="red") if error else Text(""),
                )

        return table
