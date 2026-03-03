"""Git panel — branch, status, staged/modified, recent commits.

Subscribes to ``AppState.git_data`` and renders Rich tables.
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

_CHANGE_ICONS: dict[str, str] = {
    "A": "[green]+[/]",
    "M": "[yellow]~[/]",
    "D": "[red]−[/]",
    "R": "[cyan]→[/]",
}


class GitPanel(Static):
    """Panel displaying git repository information."""

    git_data: reactive[dict[str, Any]] = reactive({}, always_update=True)

    DEFAULT_CSS = """
    GitPanel {
        height: 100%;
        overflow-y: auto;
    }
    """

    def render(self) -> Table | Text:
        data = self.git_data
        if not data:
            return Text("⏳ Awaiting Git data…", style="dim italic")

        if not data.get("available", False):
            return Text(
                "📦 No Git repository detected\n\n"
                "Run `git init` or open a project\n"
                "that contains a Git repository.",
                style="dim",
            )

        try:
            return self._build_table(data)
        except Exception:
            logger.exception("GitPanel render error")
            return Text("⚠ Failed to render Git data", style="bold red")

    def _build_table(self, data: dict[str, Any]) -> Table:
        branch = data.get("branch", "?")
        is_dirty = data.get("is_dirty", False)
        staged = data.get("staged_files", [])
        modified = data.get("modified_files", [])
        untracked = data.get("untracked_files", [])
        head = data.get("head_commit") or {}
        commits = data.get("recent_commits", [])
        stash = data.get("stash_count", 0)

        dirty_marker = " [bold red]●[/]" if is_dirty else " [green]✔[/]"

        table = Table(
            title=f"📦 Git  [bold]{branch}[/]{dirty_marker}",
            title_style="bold cyan",
            expand=True,
            show_edge=False,
            pad_edge=False,
        )
        table.add_column("", ratio=1)
        table.add_column("", ratio=4)

        # HEAD commit
        if head:
            table.add_row(
                Text("HEAD", style="bold"),
                f"[dim]{head.get('short_sha', '?')}[/] {head.get('message', '')}",
            )

        # Stats row
        stats_parts: list[str] = []
        if staged:
            stats_parts.append(f"[green]{len(staged)} staged[/]")
        if modified:
            stats_parts.append(f"[yellow]{len(modified)} modified[/]")
        if untracked:
            stats_parts.append(f"[red]{len(untracked)} untracked[/]")
        if stash:
            stats_parts.append(f"[cyan]{stash} stash(es)[/]")
        if stats_parts:
            table.add_row("Status", "  ".join(stats_parts))

        # Staged files
        if staged:
            table.add_section()
            table.add_row(Text("Staged", style="bold green"), "")
            for f in staged[:8]:
                icon = _CHANGE_ICONS.get(f.get("change_type", "M"), "?")
                table.add_row("", f"  {icon} {f.get('path', '?')}")

        # Modified files
        if modified:
            table.add_section()
            table.add_row(Text("Modified", style="bold yellow"), "")
            for f in modified[:8]:
                icon = _CHANGE_ICONS.get(f.get("change_type", "M"), "?")
                table.add_row("", f"  {icon} {f.get('path', '?')}")

        # Recent commits
        if commits:
            table.add_section()
            table.add_row(Text("Recent Commits", style="bold"), "")
            for c in commits[:5]:
                sha = c.get("short_sha", "?")
                msg = c.get("message", "")[:50]
                author = c.get("author", "")
                table.add_row("", f"  [dim]{sha}[/] {msg}  [dim]({author})[/]")

        return table
