"""DevCommand — Textual application engine.

This module bootstraps the TUI:

1. ``main()`` parses CLI flags, loads config, initialises logging
2. ``DevCommandApp`` composes six panels in a 3x2 CSS grid
3. On mount it logs platform info, binds state to panels, and
   installs the log handler so the LogsPanel receives messages.
4. Error isolation: any panel crash is caught and rendered locally.

Data flow (prepared for async services)::

    (future scheduler) → AppState → BasePanel.refresh_content() → render
"""

from __future__ import annotations

import contextlib
import logging
import sys
from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Header, Static

from devcommand.__version__ import __version__
from devcommand.config.settings import AppSettings, load_settings
from devcommand.core.state import AppState
from devcommand.ui.panels.base import BasePanel
from devcommand.ui.panels.docker_panel import DockerPanel
from devcommand.ui.panels.git_panel import GitPanel
from devcommand.ui.panels.logs_panel import LogsPanel, StateLogHandler
from devcommand.ui.panels.server_panel import ServerPanel
from devcommand.ui.panels.system_panel import SystemPanel
from devcommand.ui.panels.todo_panel import TodoPanel
from devcommand.utils.logging import configure_logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Panel wrapper — bordered container with title
# ---------------------------------------------------------------------------

class _PanelSlot(Container):
    """Wraps a :class:`BasePanel` in a titled border container."""

    def __init__(self, title: str, panel_id: str, panel: BasePanel) -> None:
        super().__init__(panel, id=panel_id, classes="panel")
        self._title = title

    def compose(self) -> ComposeResult:
        yield Static(self._title, classes="panel-title")


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class DevCommandApp(App[None]):
    """Textual TUI application for DevCommand.

    The app owns the :class:`AppState` and passes it to each
    panel on mount.  Services (not implemented yet) will push
    data into state; panels read from it.
    """

    TITLE = "DevCommand"
    SUB_TITLE = "Developer Command Center"
    CSS_PATH: ClassVar[str] = "ui/layout.css"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("d", "toggle_dark", "Toggle Dark", show=True),
        Binding("r", "refresh_panels", "Refresh", show=True),
        Binding("t", "cycle_theme", "Theme", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("1", "focus_panel('panel-git')", "Git", show=False),
        Binding("2", "focus_panel('panel-docker')", "Docker", show=False),
        Binding("3", "focus_panel('panel-system')", "System", show=False),
        Binding("4", "focus_panel('panel-todo')", "Todo", show=False),
        Binding("5", "focus_panel('panel-server')", "Server", show=False),
        Binding("6", "focus_panel('panel-logs')", "Logs", show=False),
    ]

    def __init__(
        self,
        settings: AppSettings | None = None,
        debug: bool = False,
    ) -> None:
        super().__init__()
        self.settings: AppSettings = settings or load_settings()
        self.app_state: AppState = AppState()
        self._debug = debug

        # Create panels (stored as attrs for lifecycle access)
        self._git_panel = GitPanel(id="git-inner")
        self._docker_panel = DockerPanel(id="docker-inner")
        self._system_panel = SystemPanel(id="system-inner")
        self._todo_panel = TodoPanel(id="todo-inner")
        self._server_panel = ServerPanel(id="server-inner")
        self._logs_panel = LogsPanel(id="logs-inner")

    # -- composition --------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # Row 1: Git  |  Docker  |  System
        yield _PanelSlot("📦 Git", "panel-git", self._git_panel)
        yield _PanelSlot("🐳 Docker", "panel-docker", self._docker_panel)
        yield _PanelSlot("⚡ System", "panel-system", self._system_panel)

        # Row 2: Todo  |  Server  |  Logs
        yield _PanelSlot("📋 TODO", "panel-todo", self._todo_panel)
        yield _PanelSlot("🌐 Server", "panel-server", self._server_panel)
        yield _PanelSlot("📝 Logs", "panel-logs", self._logs_panel)

        yield Static("", id="error-banner")
        yield Footer()

    # -- lifecycle ----------------------------------------------------------

    async def on_mount(self) -> None:
        """Called when the app DOM is ready."""
        # Log platform info
        from devcommand.core.platform import platform_info
        info = platform_info()
        logger.info(
            "DevCommand v%s mounted — %s/%s, Python %s, workspace=%s",
            __version__, info.os, info.arch, info.python_version,
            self.settings.workspace_path or Path.cwd(),
        )

        # Apply theme
        self.dark = self.settings.ui.theme != "light"

        # Bind state to all panels
        for panel in self._all_panels:
            panel.bind_state(self.app_state)

        # Install log handler so LogsPanel receives messages
        log_handler = StateLogHandler(self.app_state)
        log_handler.setLevel(logging.DEBUG if self._debug else logging.INFO)
        logging.getLogger().addHandler(log_handler)

        # Initial render
        self._refresh_all_panels()

        logger.info("Lifecycle: mount complete — %d panels active", len(self._all_panels))

    async def on_unmount(self) -> None:
        """Clean shutdown — safe for Windows (no signal handling)."""
        logger.info("Lifecycle: shutdown initiated")
        # Remove our log handler to avoid dangling references
        root = logging.getLogger()
        for handler in list(root.handlers):
            if isinstance(handler, StateLogHandler):
                root.removeHandler(handler)
        logger.info("Lifecycle: shutdown complete")

    # -- panel refresh (placeholder for future scheduler) -------------------

    def _refresh_all_panels(self) -> None:
        """Push state into each panel's render cycle."""
        for panel in self._all_panels:
            panel.refresh_content()

    # -- actions ------------------------------------------------------------

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    async def action_refresh_panels(self) -> None:
        """Manual refresh via 'r' key."""
        logger.info("Manual refresh triggered")
        self._refresh_all_panels()

    def action_focus_panel(self, panel_id: str) -> None:
        """Focus a panel by ID (keys 1-6)."""
        with contextlib.suppress(Exception):
            self.query_one(f"#{panel_id}").focus()

    def action_cycle_theme(self) -> None:
        """Cycle through available themes."""
        from devcommand.config.themes import available_themes
        themes = available_themes()
        current = self.settings.ui.theme
        try:
            idx = themes.index(current)
        except ValueError:
            idx = 0
        next_theme = themes[(idx + 1) % len(themes)]
        self.settings.ui.theme = next_theme
        self.dark = next_theme != "light"
        logger.info("Theme: %s", next_theme)

    def action_show_help(self) -> None:
        """Show keyboard shortcut overlay."""
        help_text = (
            "Keyboard shortcuts:\n"
            "  q — Quit          d — Dark mode\n"
            "  r — Refresh       t — Cycle theme\n"
            "  1-6 — Focus panel\n"
            "  ? — This help"
        )
        try:
            banner = self.query_one("#error-banner", Static)
            banner.update(help_text)
            banner.add_class("visible")
        except Exception:
            pass

    # -- error boundary -----------------------------------------------------

    def on_exception(self, error: Exception) -> None:
        """Global error boundary — log and display, do not crash."""
        logger.exception("Unhandled error: %s", error)
        try:
            banner = self.query_one("#error-banner", Static)
            banner.update(f"⚠ {error}")
            banner.add_class("visible")
        except Exception:
            pass
        self.app_state.record_error(str(error))

    # -- helpers ------------------------------------------------------------

    @property
    def _all_panels(self) -> list[BasePanel]:
        return [
            self._git_panel,
            self._docker_panel,
            self._system_panel,
            self._todo_panel,
            self._server_panel,
            self._logs_panel,
        ]


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entrypoint: flags → config → logging → TUI.

    Order of operations:
    1. Parse CLI arguments
    2. Load config file (with CLI overrides)
    3. Initialise structured logging
    4. Instantiate and run the Textual app
    """
    from devcommand.cli import parse_args
    from devcommand.utils.profiling import profiler

    args = parse_args()

    # Load settings, apply CLI overrides
    settings = load_settings()
    if args.refresh is not None:
        settings.scheduler.tick_interval = args.refresh
    if args.workspace != Path.cwd():
        settings.workspace_path = args.workspace
    if args.no_plugins:
        settings.plugins.enabled = False
    if args.debug:
        settings.debug_mode = True

    # Initialise logging
    configure_logging(
        level=logging.DEBUG if args.debug else logging.INFO,
        debug=args.debug,
    )

    # Profiling
    profiler.enabled = args.profile

    logger.info(
        "Starting DevCommand v%s (workspace=%s, debug=%s)",
        __version__, args.workspace, args.debug,
    )

    try:
        app = DevCommandApp(settings=settings, debug=args.debug)
        app.run()
    except KeyboardInterrupt:
        logger.info("DevCommand interrupted by user")
    except Exception:
        logger.exception("Fatal error in DevCommand")
        sys.exit(1)
    finally:
        if profiler.enabled:
            profiler.report()


if __name__ == "__main__":
    main()
