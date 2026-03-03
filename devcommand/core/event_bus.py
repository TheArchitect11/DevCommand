"""Core event bus for decoupled inter-component communication."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# Type alias for async event handlers
EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """A lightweight async event bus for publish/subscribe messaging.

    Enables loose coupling between services, panels, and plugins.
    All handlers are invoked concurrently via ``asyncio.gather``.

    Example::

        bus = EventBus()

        async def on_cpu_spike(percent: float) -> None:
            print(f"CPU at {percent}%")

        bus.subscribe("system.cpu.spike", on_cpu_spike)
        await bus.publish("system.cpu.spike", percent=92.5)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event: str, handler: EventHandler) -> None:
        """Register *handler* for *event*."""
        self._handlers[event].append(handler)
        logger.debug("Subscribed %s to event '%s'", handler.__qualname__, event)

    def unsubscribe(self, event: str, handler: EventHandler) -> None:
        """Remove *handler* from *event*."""
        try:
            self._handlers[event].remove(handler)
        except ValueError:
            logger.warning(
                "Handler %s was not subscribed to '%s'", handler.__qualname__, event
            )

    async def publish(self, event: str, **kwargs: Any) -> None:
        """Fan-out *event* to all subscribed handlers concurrently."""
        handlers = self._handlers.get(event, [])
        if not handlers:
            return
        logger.debug("Publishing event '%s' to %d handler(s)", event, len(handlers))
        results = await asyncio.gather(
            *(h(**kwargs) for h in handlers), return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error("Handler error on event '%s': %s", event, result)
