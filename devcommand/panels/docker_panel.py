"""Docker panel — container and image tables.

Subscribes to ``AppState.docker_data`` and renders Rich tables.
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
    "running": "bold green",
    "exited": "red",
    "paused": "yellow",
    "restarting": "cyan",
    "created": "dim",
    "dead": "bold red",
    "removing": "dim red",
}


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n //= 1024  # type: ignore[assignment]
    return f"{n:.1f} TB"


class DockerPanel(Static):
    """Panel displaying Docker container and image status."""

    docker_data: reactive[dict[str, Any]] = reactive({}, always_update=True)

    DEFAULT_CSS = """
    DockerPanel {
        height: 100%;
        overflow-y: auto;
    }
    """

    def render(self) -> Table | Text:
        data = self.docker_data
        if not data:
            return Text("⏳ Awaiting Docker data…", style="dim italic")

        if not data.get("available", False):
            return Text(
                "🐳 Docker daemon unavailable\n\n"
                "Start Docker Desktop or the Docker daemon\n"
                "to see container information here.",
                style="dim",
            )

        try:
            return self._build_table(data)
        except Exception:
            logger.exception("DockerPanel render error")
            return Text("⚠ Failed to render Docker data", style="bold red")

    def _build_table(self, data: dict[str, Any]) -> Table:
        containers = data.get("containers", [])
        images = data.get("images", [])
        running = data.get("running_count", 0)
        stopped = data.get("stopped_count", 0)
        total = data.get("total_count", 0)

        # -- Container table --
        table = Table(
            title=f"🐳 Docker  [dim]({running} running / {total} total)[/]",
            title_style="bold cyan",
            expand=True,
            show_edge=False,
            pad_edge=False,
        )
        table.add_column("Name", style="bold", ratio=2)
        table.add_column("Image", ratio=2)
        table.add_column("Status", ratio=1)
        table.add_column("ID", style="dim", ratio=1)

        if not containers:
            table.add_row("—", "No containers found", "", "")
        else:
            for c in containers:
                status_str = c.get("status", "unknown")
                style = _STATUS_STYLES.get(status_str, "")
                table.add_row(
                    c.get("name", "?"),
                    c.get("image", "?"),
                    Text(status_str, style=style),
                    c.get("id", "?"),
                )

        # -- Images summary row --
        if images:
            table.add_section()
            table.add_row(
                Text(f"📦 {len(images)} image(s)", style="bold"),
                "",
                "",
                "",
            )
            for img in images[:5]:
                tags = ", ".join(img.get("tags", [])) or "—"
                table.add_row(
                    f"  {tags}",
                    _human_bytes(img.get("size_bytes", 0)),
                    "",
                    img.get("id", "?"),
                )

        return table
