"""Todo panel — displays task list."""

from __future__ import annotations

from rich.text import Text

from devcommand.ui.panels.base import BasePanel


class TodoPanel(BasePanel):
    """Shows TODO items with status and priority."""

    def build_content(self) -> Text:
        data = self.state.todo_state
        if not data:
            return Text("📋 No TODOs yet\n\nItems will appear here when added.", style="dim")

        items = data.get("items", [])
        if not items:
            return Text("📋 No TODOs yet", style="dim")

        pending = sum(1 for i in items if i.get("status") == "pending")
        done = sum(1 for i in items if i.get("status") == "done")

        lines = [f"Tasks: {len(items)} ({pending} pending, {done} done)", ""]
        for item in items[:8]:  # show top 8
            icon = "●" if item.get("status") == "done" else "○"
            prio = item.get("priority", "").upper()[:3]
            lines.append(f"  {icon} [{prio}] {item.get('title', '?')}")

        return Text("\n".join(lines))
