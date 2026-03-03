"""Base panel protocol for Textual UI panels."""

from __future__ import annotations

from abc import abstractmethod

from textual.widget import Widget


class BasePanel(Widget):
    """Abstract base for all TUI panels.

    Panels are self-contained UI sections that can be composed into the
    main application layout.  Each panel may optionally subscribe to
    :class:`~devcommand.core.event_bus.EventBus` events to react to
    service updates.
    """

    @abstractmethod
    def compose_panel(self) -> None:
        """Set up the panel's child widgets.

        Subclasses must implement this; it is called from ``compose()``.
        """
        ...

    @abstractmethod
    async def on_panel_mount(self) -> None:
        """Hook invoked after the panel is mounted.

        Use this to subscribe to events or kick off background polling.
        """
        ...
