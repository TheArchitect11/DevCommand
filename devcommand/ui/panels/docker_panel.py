"""Docker panel — displays container and image overview."""

from __future__ import annotations

from rich.text import Text

from devcommand.ui.panels.base import BasePanel


class DockerPanel(BasePanel):
    """Shows Docker containers, images, daemon status."""

    def build_content(self) -> Text:
        data = self.state.docker_state
        if not data:
            return Text("⏳ Awaiting Docker data…", style="dim")
        if not data.get("available", True):
            return Text("🐳 Docker daemon unavailable", style="yellow")

        containers = data.get("containers", [])
        images = data.get("images", [])
        running = sum(1 for c in containers if c.get("status") == "running")

        lines = [
            f"Containers: {len(containers)} ({running} running)",
            f"Images: {len(images)}",
        ]
        return Text("\n".join(lines))
