"""Base plugin protocol for the plugin system.

Plugins extend :class:`BasePlugin` and implement lifecycle hooks.
The loader instantiates them; the registry manages activation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from devcommand.core.app_state import AppState
    from devcommand.core.event_bus import EventBus
    from devcommand.plugins.manifest import PluginManifest


class BasePlugin(ABC):
    """Abstract base class for DevCommand plugins.

    Subclasses **must** implement :meth:`activate` and :meth:`deactivate`.

    Optional hooks:

    * :meth:`get_panels` — return panel widget instances to mount
    * :meth:`get_services` — return service instances to register
    * :meth:`get_scheduler_jobs` — return ``JobConfig`` list for the scheduler
    """

    def __init__(self, manifest: PluginManifest | None = None) -> None:
        self._manifest = manifest
        self._active = False

    # -- identity -----------------------------------------------------------

    @property
    def name(self) -> str:
        """Plugin name (from manifest or override)."""
        return self._manifest.name if self._manifest else self.__class__.__name__

    @property
    def version(self) -> str:
        """Plugin version (from manifest or override)."""
        return self._manifest.version if self._manifest else "0.0.0"

    @property
    def is_active(self) -> bool:
        return self._active

    # -- lifecycle ----------------------------------------------------------

    @abstractmethod
    async def activate(self, event_bus: EventBus, app_state: AppState) -> None:
        """Called when the plugin is activated.

        Subscribe to events, initialise resources, etc.
        """
        ...

    @abstractmethod
    async def deactivate(self) -> None:
        """Called on shutdown. Release resources, unsubscribe."""
        ...

    # -- extension hooks (optional) -----------------------------------------

    def get_panels(self) -> list[Any]:
        """Return panel widget instances to mount in the UI.

        Override to provide custom panels.
        """
        return []

    def get_services(self) -> list[Any]:
        """Return service instances to register with the scheduler.

        Override to provide custom services.
        """
        return []

    def get_scheduler_jobs(self) -> list[Any]:
        """Return ``JobConfig`` instances for the central scheduler.

        Override to register custom background jobs.
        """
        return []
