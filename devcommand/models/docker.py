"""Pydantic models for Docker entities."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ContainerStatus(StrEnum):
    """Possible Docker container states."""

    RUNNING = "running"
    EXITED = "exited"
    PAUSED = "paused"
    RESTARTING = "restarting"
    CREATED = "created"
    DEAD = "dead"
    REMOVING = "removing"
    UNKNOWN = "unknown"


class ContainerInfo(BaseModel):
    """Summary of a Docker container."""

    id: str = Field(description="Short container ID")
    name: str = Field(description="Container name")
    status: ContainerStatus = Field(description="Container state")
    image: str = Field(description="Image tag")
    ports: dict[str, str | None] = Field(
        default_factory=dict, description="Port mappings (container → host)"
    )
    created: datetime | None = Field(default=None, description="Creation timestamp")


class ImageInfo(BaseModel):
    """Summary of a Docker image."""

    id: str = Field(description="Short image ID")
    tags: list[str] = Field(default_factory=list, description="Image tags")
    size_bytes: int = Field(ge=0, description="Image size in bytes")


class DockerSnapshot(BaseModel):
    """Aggregated Docker daemon state."""

    available: bool = Field(description="Whether the Docker daemon is reachable")
    containers: list[ContainerInfo] = Field(default_factory=list)
    images: list[ImageInfo] = Field(default_factory=list)
    running_count: int = Field(ge=0, default=0)
    stopped_count: int = Field(ge=0, default=0)
    total_count: int = Field(ge=0, default=0)
    timestamp: datetime = Field(default_factory=datetime.now)
