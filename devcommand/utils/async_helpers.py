"""Async helper utilities."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


async def run_in_executor(func: Callable[..., T], *args: object) -> T:
    """Run a synchronous *func* in the default thread-pool executor.

    This is a convenience wrapper to keep blocking calls off the
    Textual / asyncio event loop.

    Args:
        func: The synchronous callable to execute.
        *args: Positional arguments forwarded to *func*.

    Returns:
        The return value of *func*.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)
