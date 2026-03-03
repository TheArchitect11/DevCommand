"""Pydantic models for system metrics."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CpuMetrics(BaseModel):
    """CPU usage snapshot."""

    percent: float = Field(ge=0, le=100, description="CPU usage percentage")
    core_count: int = Field(ge=1, description="Number of logical CPU cores")
    frequency_mhz: float | None = Field(
        default=None, ge=0, description="Current CPU frequency in MHz"
    )


class MemoryMetrics(BaseModel):
    """Memory usage snapshot."""

    total: int = Field(ge=0, description="Total physical memory in bytes")
    used: int = Field(ge=0, description="Used memory in bytes")
    available: int = Field(ge=0, description="Available memory in bytes")
    percent: float = Field(ge=0, le=100, description="Memory usage percentage")


class DiskMetrics(BaseModel):
    """Disk usage snapshot."""

    total: int = Field(ge=0, description="Total disk space in bytes")
    used: int = Field(ge=0, description="Used disk space in bytes")
    free: int = Field(ge=0, description="Free disk space in bytes")
    percent: float = Field(ge=0, le=100, description="Disk usage percentage")


class NetworkMetrics(BaseModel):
    """Network I/O counters snapshot."""

    bytes_sent: int = Field(ge=0, description="Total bytes sent")
    bytes_recv: int = Field(ge=0, description="Total bytes received")
    packets_sent: int = Field(ge=0, description="Total packets sent")
    packets_recv: int = Field(ge=0, description="Total packets received")


class ProcessInfo(BaseModel):
    """Summary of a running process."""

    pid: int
    name: str
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    status: str = "running"


class SystemSnapshot(BaseModel):
    """Aggregated system metrics snapshot."""

    cpu: CpuMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    network: NetworkMetrics
    top_processes: list[ProcessInfo] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    uptime_seconds: float = Field(ge=0, default=0.0)
