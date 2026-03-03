"""Server health panel — endpoint monitoring."""

from __future__ import annotations

from rich.text import Text

from devcommand.ui.panels.base import BasePanel


class ServerPanel(BasePanel):
    """Shows server health check results."""

    def build_content(self) -> Text:
        data = self.state.server_state
        if not data:
            return Text("🌐 No health endpoints configured\n\nAdd endpoints in .devcommand.yml",
                        style="dim")

        endpoints = data.get("endpoints", [])
        if not endpoints:
            return Text("🌐 No endpoints configured", style="dim")

        lines = []
        for ep in endpoints:
            icon = "🟢" if ep.get("healthy") else "🔴"
            name = ep.get("name", ep.get("url", "?"))
            code = ep.get("status_code", "—")
            ms = ep.get("response_time_ms")
            time_str = f" ({ms:.0f}ms)" if ms is not None else ""
            lines.append(f"  {icon} {name}: {code}{time_str}")

        return Text("\n".join(lines))
