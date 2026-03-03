"""File-backed TODO tracking service.

Persists TODO items as JSON in ``~/.devcommand/todos.json``.
All file I/O is dispatched to a thread-pool executor.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

from devcommand.core.base_service import BaseService
from devcommand.models.todo import TodoItem, TodoPriority, TodoSnapshot, TodoStatus
from devcommand.utils.cache import TTLCache

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path.home() / ".devcommand" / "todos.json"


class TodoService(BaseService):
    """Async TODO service with JSON file persistence.

    Pure data layer — no UI dependencies.  Easily mockable via
    constructor injection of the storage path.

    Usage::

        service = TodoService(storage_path=Path("/tmp/todos.json"))
        await service.start()
        item = await service.add("Fix login bug", priority=TodoPriority.HIGH)
        snapshot = await service.get_snapshot()
    """

    def __init__(
        self,
        storage_path: Path | None = None,
        cache_ttl: float = 1.0,
    ) -> None:
        super().__init__()
        self._path = storage_path or _DEFAULT_PATH
        self._items: list[TodoItem] = []
        self._cache: TTLCache[TodoSnapshot] = TTLCache(ttl=cache_ttl)

    async def start(self) -> None:
        """Load existing TODOs from disk."""
        await super().start()
        loop = asyncio.get_running_loop()
        self._items = await loop.run_in_executor(None, self._load)
        logger.info("TodoService loaded %d item(s) from %s", len(self._items), self._path)

    async def stop(self) -> None:
        """Persist TODOs to disk and clear cache."""
        await self._persist()
        self._cache.clear()
        await super().stop()

    # -- public API ---------------------------------------------------------

    async def get_snapshot(self) -> TodoSnapshot:
        """Return aggregated TODO state (cached)."""
        cached = self._cache.get("snapshot")
        if cached is not None:
            return cached

        pending = sum(1 for i in self._items if i.status == TodoStatus.PENDING)
        done = sum(1 for i in self._items if i.status == TodoStatus.DONE)

        snapshot = TodoSnapshot(
            items=list(self._items),
            pending_count=pending,
            done_count=done,
            total_count=len(self._items),
        )
        self._cache.set("snapshot", snapshot)
        return snapshot

    async def add(
        self,
        title: str,
        description: str = "",
        priority: TodoPriority = TodoPriority.MEDIUM,
        tags: list[str] | None = None,
    ) -> TodoItem:
        """Create and persist a new TODO item."""
        item = TodoItem(
            title=title,
            description=description,
            priority=priority,
            tags=tags or [],
        )
        self._items.append(item)
        self._cache.invalidate("snapshot")
        await self._persist()
        logger.info("Added TODO: %s (id=%s)", title, item.id)
        return item

    async def update_status(self, item_id: UUID, status: TodoStatus) -> TodoItem | None:
        """Update the status of an existing item."""
        for i, item in enumerate(self._items):
            if item.id == item_id:
                self._items[i] = item.model_copy(
                    update={"status": status, "updated_at": datetime.now()}
                )
                self._cache.invalidate("snapshot")
                await self._persist()
                return self._items[i]
        return None

    async def remove(self, item_id: UUID) -> bool:
        """Remove a TODO item by ID."""
        before = len(self._items)
        self._items = [i for i in self._items if i.id != item_id]
        if len(self._items) < before:
            self._cache.invalidate("snapshot")
            await self._persist()
            return True
        return False

    async def get_by_priority(self, priority: TodoPriority) -> list[TodoItem]:
        """Filter items by priority."""
        return [i for i in self._items if i.priority == priority]

    async def get_by_status(self, status: TodoStatus) -> list[TodoItem]:
        """Filter items by status."""
        return [i for i in self._items if i.status == status]

    # -- persistence (sync, runs in executor) --------------------------------

    async def _persist(self) -> None:
        """Save items to disk in a background thread."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save)

    def _save(self) -> None:
        """Write items to JSON file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [item.model_dump(mode="json") for item in self._items]
        self._path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.debug("Persisted %d TODO(s) to %s", len(data), self._path)

    def _load(self) -> list[TodoItem]:
        """Read items from JSON file."""
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return [TodoItem.model_validate(item) for item in raw]
        except Exception:
            logger.warning("Failed to load TODOs from %s", self._path, exc_info=True)
            return []
