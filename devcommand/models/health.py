"""Pydantic models for server health checks."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    """Possible health states for a monitored endpoint."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class EndpointHealth(BaseModel):
    """Health check result for a single endpoint."""

    name: str = Field(description="Human-readable endpoint name")
    url: str = Field(description="URL that was checked")
    status: HealthStatus = Field(default=HealthStatus.UNKNOWN)
    status_code: int | None = Field(default=None, description="HTTP status code")
    response_time_ms: float | None = Field(
        default=None, ge=0, description="Response time in milliseconds"
    )
    error: str | None = Field(default=None, description="Error message if unhealthy")
    last_checked: datetime = Field(default_factory=datetime.now)


class ServerHealthSnapshot(BaseModel):
    """Aggregated health of all monitored endpoints."""

    endpoints: list[EndpointHealth] = Field(default_factory=list)
    healthy_count: int = Field(ge=0, default=0)
    unhealthy_count: int = Field(ge=0, default=0)
    timestamp: datetime = Field(default_factory=datetime.now)
