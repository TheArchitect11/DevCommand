"""Git panel — displays repository status."""

from __future__ import annotations

from rich.text import Text

from devcommand.ui.panels.base import BasePanel


class GitPanel(BasePanel):
    """Shows Git branch, staged/modified files, recent commits."""

    def build_content(self) -> Text:
        data = self.state.git_state
        if not data:
            return Text("⏳ Awaiting Git data…", style="dim")
        if not data.get("available", True):
            return Text("📦 No Git repository detected", style="yellow")

        branch = data.get("branch", "unknown")
        dirty = " ●" if data.get("is_dirty") else ""
        staged = len(data.get("staged", []))
        modified = len(data.get("modified", []))
        commits = len(data.get("recent_commits", []))

        lines = [
            f"Branch: {branch}{dirty}",
            f"Staged: {staged}  Modified: {modified}",
            f"Recent commits: {commits}",
        ]
        return Text("\n".join(lines))
