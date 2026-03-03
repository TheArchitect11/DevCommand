"""Pydantic models for the TODO tracking service."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TodoPriority(StrEnum):
    """Priority levels for TODO items."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TodoStatus(StrEnum):
    """Lifecycle states for a TODO item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TodoItem(BaseModel):
    """A single TODO item."""

    id: UUID = Field(default_factory=uuid4, description="Unique item ID")
    title: str = Field(min_length=1, max_length=200, description="Short description")
    description: str = Field(default="", description="Optional detailed description")
    priority: TodoPriority = Field(default=TodoPriority.MEDIUM)
    status: TodoStatus = Field(default=TodoStatus.PENDING)
    tags: list[str] = Field(default_factory=list, description="Freeform tags")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def mark_done(self) -> TodoItem:
        """Return a copy marked as done."""
        return self.model_copy(
            update={"status": TodoStatus.DONE, "updated_at": datetime.now()}
        )


class TodoSnapshot(BaseModel):
    """Aggregated TODO state."""

    items: list[TodoItem] = Field(default_factory=list)
    pending_count: int = Field(ge=0, default=0)
    done_count: int = Field(ge=0, default=0)
    total_count: int = Field(ge=0, default=0)
