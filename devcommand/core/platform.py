"""Cross-platform detection layer.

Uses **only** the Python standard library — no shell commands,
no OS-specific calls.  All path handling uses :mod:`pathlib`.

Usage::

    from devcommand.core.platform import platform_info, is_macos

    info = platform_info()
    if is_macos():
        ...
"""

from __future__ import annotations

import platform
import struct
from dataclasses import dataclass
from enum import StrEnum


class OSFamily(StrEnum):
    """Supported operating system families."""

    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


class Architecture(StrEnum):
    """CPU architecture."""

    ARM64 = "arm64"
    X86_64 = "x86_64"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PlatformInfo:
    """Immutable snapshot of the current platform."""

    os: OSFamily
    arch: Architecture
    python_version: str          # e.g. "3.13.2"
    python_impl: str             # e.g. "CPython"
    pointer_size: int            # 4 or 8
    os_release: str              # kernel / build version
    hostname: str

    @property
    def is_64bit(self) -> bool:
        return self.pointer_size == 8


def _detect_os() -> OSFamily:
    name = platform.system().lower()
    if name == "darwin":
        return OSFamily.MACOS
    if name == "windows":
        return OSFamily.WINDOWS
    if name == "linux":
        return OSFamily.LINUX
    return OSFamily.UNKNOWN


def _detect_arch() -> Architecture:
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return Architecture.ARM64
    if machine in ("x86_64", "amd64", "x86"):
        return Architecture.X86_64
    return Architecture.UNKNOWN


def platform_info() -> PlatformInfo:
    """Detect and return the current platform information."""
    return PlatformInfo(
        os=_detect_os(),
        arch=_detect_arch(),
        python_version=platform.python_version(),
        python_impl=platform.python_implementation(),
        pointer_size=struct.calcsize("P"),
        os_release=platform.release(),
        hostname=platform.node(),
    )


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def is_windows() -> bool:
    """True if running on Windows."""
    return platform.system().lower() == "windows"


def is_macos() -> bool:
    """True if running on macOS (Darwin)."""
    return platform.system().lower() == "darwin"


def is_linux() -> bool:
    """True if running on Linux."""
    return platform.system().lower() == "linux"


def is_arm64() -> bool:
    """True if architecture is ARM64 / Apple Silicon."""
    return _detect_arch() == Architecture.ARM64
