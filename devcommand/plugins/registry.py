"""Plugin registry — manages plugin lifecycle with failure isolation.

Owns the list of loaded plugins and coordinates activation,
deactivation, and introspection.  Integrates with the scheduler
and panel system via the hooks on :class:`BasePlugin`.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from devcommand.core.app_state import AppState
    from devcommand.core.event_bus import EventBus

from devcommand.core.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class PluginState(StrEnum):
    """Lifecycle state of a registered plugin."""

    LOADED = "loaded"
    ACTIVE = "active"
    FAILED = "failed"
    DISABLED = "disabled"


class PluginEntry:
    """Wrapper tracking a plugin and its lifecycle state."""

    __slots__ = ("error", "plugin", "state")

    def __init__(self, plugin: BasePlugin, state: PluginState = PluginState.LOADED) -> None:
        self.plugin = plugin
        self.state = state
        self.error: str | None = None

    def __repr__(self) -> str:
        return f"<PluginEntry {self.plugin.name} [{self.state}]>"


class PluginRegistry:
    """Manages plugin lifecycle: registration, activation, deactivation.

    Failure isolation: a single plugin failure never propagates to
    other plugins or the host application.
    """

    def __init__(self) -> None:
        self._entries: dict[str, PluginEntry] = {}

    # -- registration -------------------------------------------------------

    def register(self, plugin: BasePlugin) -> None:
        """Add a loaded plugin to the registry."""
        name = plugin.name
        if name in self._entries:
            logger.warning("Plugin '%s' already registered — skipping duplicate", name)
            return
        self._entries[name] = PluginEntry(plugin)
        logger.info("Registered plugin: %s v%s", name, plugin.version)

    def register_many(self, plugins: list[BasePlugin]) -> None:
        """Register multiple plugins at once."""
        for p in plugins:
            self.register(p)

    # -- activation ---------------------------------------------------------

    async def activate_all(self, event_bus: EventBus, app_state: AppState) -> None:
        """Activate every registered (and non-failed) plugin."""
        for entry in self._entries.values():
            if entry.state != PluginState.LOADED:
                continue
            await self._activate_one(entry, event_bus, app_state)

    async def activate_one(self, name: str, event_bus: EventBus, app_state: AppState) -> bool:
        """Activate a single plugin by name. Returns True on success."""
        entry = self._entries.get(name)
        if entry is None:
            logger.warning("Cannot activate unknown plugin: %s", name)
            return False
        return await self._activate_one(entry, event_bus, app_state)

    async def _activate_one(
        self, entry: PluginEntry, event_bus: EventBus, app_state: AppState
    ) -> bool:
        name = entry.plugin.name
        try:
            await entry.plugin.activate(event_bus, app_state)
            entry.plugin._active = True
            entry.state = PluginState.ACTIVE
            logger.info("Activated plugin: %s", name)
            return True
        except Exception as exc:
            entry.state = PluginState.FAILED
            entry.error = str(exc)
            logger.exception("Failed to activate plugin: %s", name)
            return False

    # -- deactivation -------------------------------------------------------

    async def deactivate_all(self) -> None:
        """Deactivate every active plugin (reverse order)."""
        for entry in reversed(list(self._entries.values())):
            if entry.state != PluginState.ACTIVE:
                continue
            await self._deactivate_one(entry)

    async def deactivate_one(self, name: str) -> bool:
        """Deactivate a single plugin by name."""
        entry = self._entries.get(name)
        if entry is None or entry.state != PluginState.ACTIVE:
            return False
        return await self._deactivate_one(entry)

    async def _deactivate_one(self, entry: PluginEntry) -> bool:
        name = entry.plugin.name
        try:
            await entry.plugin.deactivate()
            entry.plugin._active = False
            entry.state = PluginState.LOADED
            logger.info("Deactivated plugin: %s", name)
            return True
        except Exception as exc:
            entry.state = PluginState.FAILED
            entry.error = str(exc)
            logger.exception("Failed to deactivate plugin: %s", name)
            return False

    # -- introspection ------------------------------------------------------

    def get_all_panels(self) -> list[Any]:
        """Collect panels from all active plugins."""
        panels: list[Any] = []
        for entry in self._entries.values():
            if entry.state == PluginState.ACTIVE:
                try:
                    panels.extend(entry.plugin.get_panels())
                except Exception:
                    logger.exception("Error getting panels from %s", entry.plugin.name)
        return panels

    def get_all_services(self) -> list[Any]:
        """Collect services from all active plugins."""
        services: list[Any] = []
        for entry in self._entries.values():
            if entry.state == PluginState.ACTIVE:
                try:
                    services.extend(entry.plugin.get_services())
                except Exception:
                    logger.exception("Error getting services from %s", entry.plugin.name)
        return services

    def get_all_scheduler_jobs(self) -> list[Any]:
        """Collect scheduler jobs from all active plugins."""
        jobs: list[Any] = []
        for entry in self._entries.values():
            if entry.state == PluginState.ACTIVE:
                try:
                    jobs.extend(entry.plugin.get_scheduler_jobs())
                except Exception:
                    logger.exception("Error getting jobs from %s", entry.plugin.name)
        return jobs

    @property
    def entries(self) -> dict[str, PluginEntry]:
        """All registered plugin entries."""
        return dict(self._entries)

    @property
    def active_plugins(self) -> list[BasePlugin]:
        """Currently active plugins."""
        return [e.plugin for e in self._entries.values() if e.state == PluginState.ACTIVE]

    @property
    def failed_plugins(self) -> dict[str, str]:
        """Plugin name → error for failed plugins."""
        return {
            name: entry.error or "unknown"
            for name, entry in self._entries.items()
            if entry.state == PluginState.FAILED
        }

    def __len__(self) -> int:
        return len(self._entries)
