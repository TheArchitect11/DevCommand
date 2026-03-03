"""System metrics panel — CPU, memory, disk, network gauges.

Subscribes to ``AppState.system_data`` and renders Rich tables.
Makes **no** direct external calls.
"""

from __future__ import annotations

import logging
from typing import Any

from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static

logger = logging.getLogger(__name__)

_EMPTY: dict[str, Any] = {}


def _bar(percent: float, width: int = 20) -> Text:
    """Render a coloured bar gauge."""
    filled = int(percent / 100 * width)
    if percent >= 90:
        colour = "red"
    elif percent >= 70:
        colour = "yellow"
    else:
        colour = "green"
    bar = "█" * filled + "░" * (width - filled)
    return Text(f"{bar} {percent:5.1f}%", style=colour)


def _human_bytes(n: int) -> str:
    """Format bytes into a human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n //= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"


def _format_uptime(seconds: float) -> str:
    """Format seconds into d h m s."""
    d = int(seconds // 86400)
    h = int((seconds % 86400) // 3600)
    m = int((seconds % 3600) // 60)
    parts: list[str] = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    parts.append(f"{m}m")
    return " ".join(parts)


class SystemPanel(Static):
    """Panel displaying live system metrics.

    Watches ``AppState.system_data`` via the app-level watcher pattern.
    """

    system_data: reactive[dict[str, Any]] = reactive({}, always_update=True)

    DEFAULT_CSS = """
    SystemPanel {
        height: 100%;
        overflow-y: auto;
    }
    """

    def render(self) -> Table | Text:
        """Build the Rich renderable from current state."""
        data = self.system_data
        if not data:
            return Text("⏳ Awaiting system metrics…", style="dim italic")

        try:
            return self._build_table(data)
        except Exception:
            logger.exception("SystemPanel render error")
            return Text("⚠ Failed to render system metrics", style="bold red")

    def _build_table(self, data: dict[str, Any]) -> Table:
        cpu = data.get("cpu", {})
        mem = data.get("memory", {})
        disk = data.get("disk", {})
        net = data.get("network", {})
        uptime = data.get("uptime_seconds", 0)
        procs = data.get("top_processes", [])

        table = Table(
            title="⚡ System Metrics",
            title_style="bold cyan",
            expand=True,
            show_edge=False,
            pad_edge=False,
        )
        table.add_column("Metric", style="bold", ratio=1)
        table.add_column("Value", ratio=3)

        # CPU
        table.add_row("CPU", _bar(cpu.get("percent", 0)))
        table.add_row("  Cores", str(cpu.get("core_count", "?")))
        freq = cpu.get("frequency_mhz")
        if freq:
            table.add_row("  Freq", f"{freq:.0f} MHz")

        # Memory
        table.add_row("Memory", _bar(mem.get("percent", 0)))
        table.add_row(
            "  Used / Total",
            f"{_human_bytes(mem.get('used', 0))} / {_human_bytes(mem.get('total', 0))}",
        )

        # Disk
        table.add_row("Disk", _bar(disk.get("percent", 0)))
        table.add_row(
            "  Free",
            _human_bytes(disk.get("free", 0)),
        )

        # Network
        table.add_row(
            "Network ↑↓",
            f"↑ {_human_bytes(net.get('bytes_sent', 0))}  ↓ {_human_bytes(net.get('bytes_recv', 0))}",
        )

        # Uptime
        table.add_row("Uptime", _format_uptime(uptime))

        # Top processes
        if procs:
            table.add_section()
            table.add_row(
                Text("Top Processes", style="bold"),
                Text("CPU%  MEM%  Name", style="dim"),
            )
            for p in procs[:5]:
                table.add_row(
                    f"  PID {p.get('pid', '?')}",
                    f"{p.get('cpu_percent', 0):5.1f}  {p.get('memory_percent', 0):5.1f}  {p.get('name', '?')}",
                )

        return table
