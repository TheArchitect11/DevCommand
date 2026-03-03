"""Hello World — example DevCommand plugin.

Demonstrates the plugin API: manifest loading, activation/deactivation,
and panel registration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual.widgets import Static

from devcommand.core.base_plugin import BasePlugin

if TYPE_CHECKING:
    from devcommand.core.app_state import AppState
    from devcommand.core.event_bus import EventBus
    from devcommand.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)


class HelloPanel(Static):
    """A simple panel provided by the example plugin."""

    DEFAULT_CSS = """
    HelloPanel {
        height: auto;
        padding: 1 2;
    }
    """

    def render(self) -> Text:
        return Text("👋 Hello from the example plugin!", style="bold green")


class HelloWorldPlugin(BasePlugin):
    """Minimal example plugin."""

    def __init__(self, manifest: PluginManifest | None = None) -> None:
        super().__init__(manifest)
        self._panel: HelloPanel | None = None

    async def activate(self, event_bus: EventBus, app_state: AppState) -> None:
        """Create the panel and log activation."""
        self._panel = HelloPanel(id="hello-panel")
        logger.info("HelloWorldPlugin activated")

    async def deactivate(self) -> None:
        """Clean up."""
        self._panel = None
        logger.info("HelloWorldPlugin deactivated")

    def get_panels(self) -> list[Any]:
        """Return the hello panel for mounting."""
        if self._panel is not None:
            return [self._panel]
        return []
