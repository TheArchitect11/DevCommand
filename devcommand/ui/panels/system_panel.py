"""System panel — displays CPU, memory, disk metrics."""

from __future__ import annotations

from rich.text import Text

from devcommand.ui.panels.base import BasePanel


class SystemPanel(BasePanel):
    """Shows CPU, memory, disk, network, and uptime."""

    def build_content(self) -> Text:
        data = self.state.system_state
        if not data:
            return Text("⏳ Awaiting system metrics…", style="dim")

        cpu = data.get("cpu", {})
        mem = data.get("memory", {})
        disk = data.get("disk", {})

        lines = [
            f"CPU:  {cpu.get('percent', 0):.0f}%  ({cpu.get('core_count', '?')} cores)",
            f"RAM:  {mem.get('percent', 0):.0f}%",
            f"Disk: {disk.get('percent', 0):.0f}%",
        ]
        uptime = data.get("uptime_seconds")
        if uptime is not None:
            hrs = int(uptime) // 3600
            mins = (int(uptime) % 3600) // 60
            lines.append(f"Up:   {hrs}h {mins}m")
        return Text("\n".join(lines))
