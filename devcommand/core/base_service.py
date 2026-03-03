"""Base service protocol and lifecycle management."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Abstract base for all background services.

    Services follow a start → run → stop lifecycle and **must not**
    perform blocking I/O on the UI thread. Use ``asyncio`` primitives
    for all I/O-bound work.
    """

    def __init__(self) -> None:
        self._running: bool = False

    @property
    def is_running(self) -> bool:
        """Whether the service is currently active."""
        return self._running

    @abstractmethod
    async def start(self) -> None:
        """Start the service. Called once during app mount."""
        self._running = True
        logger.info("%s started", self.__class__.__name__)

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully shut down the service."""
        self._running = False
        logger.info("%s stopped", self.__class__.__name__)
