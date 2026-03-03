"""Application settings validated with Pydantic.

Supports loading from:
  1. ``.devcommand.yml`` in the current working directory (project-local)
  2. ``~/.devcommand/config.toml`` (user-global, TOML fallback)
  3. Built-in defaults
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_GLOBAL_CONFIG_DIR = Path.home() / ".devcommand"
_GLOBAL_CONFIG_FILE = _GLOBAL_CONFIG_DIR / "config.toml"
_LOCAL_CONFIG_FILE = Path.cwd() / ".devcommand.yml"


# ---------------------------------------------------------------------------
# Settings sections
# ---------------------------------------------------------------------------

class LoggingSettings(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Root log level")
    log_to_file: bool = Field(default=True, description="Enable file logging")


class MetricsSettings(BaseModel):
    """System metrics polling configuration."""

    poll_interval: float = Field(
        default=2.0, ge=0.5, le=60.0, description="Polling interval in seconds"
    )


class DockerSettings(BaseModel):
    """Docker service configuration."""

    enabled: bool = Field(default=True, description="Enable Docker integration")


class GitSettings(BaseModel):
    """Git service configuration."""

    enabled: bool = Field(default=True, description="Enable Git integration")
    repo_path: Path | None = Field(
        default=None, description="Path to git repo (defaults to cwd)"
    )


class UISettings(BaseModel):
    """UI-specific configuration."""

    refresh_interval: float = Field(
        default=1.0, ge=0.25, le=30.0,
        description="Global UI refresh interval in seconds",
    )
    theme: str = Field(
        default="dark",
        description="UI theme (dark / light / nord / dracula / solarized)",
    )
    show_header: bool = Field(default=True, description="Show the app header")
    show_footer: bool = Field(default=True, description="Show the app footer")
    enabled_panels: list[str] = Field(
        default_factory=lambda: ["system", "docker", "git", "server", "todo"],
        description="List of enabled panel names",
    )


class SchedulerSettings(BaseModel):
    """Central scheduler configuration."""

    tick_interval: float = Field(
        default=2.0, ge=0.5, le=60.0,
        description="Scheduler tick interval in seconds",
    )
    default_timeout: float = Field(
        default=10.0, ge=1.0, le=60.0,
        description="Default per-service timeout in seconds",
    )
    slow_threshold: float = Field(
        default=2.0, ge=0.5, le=30.0,
        description="Warn if a service takes longer than this (seconds)",
    )
    backoff_base: float = Field(
        default=2.0, ge=1.1, le=10.0,
        description="Exponential backoff base multiplier",
    )
    backoff_max: float = Field(
        default=120.0, ge=10.0, le=600.0,
        description="Maximum backoff delay in seconds",
    )


class PluginSettings(BaseModel):
    """Plugin system configuration."""

    enabled: bool = Field(default=True, description="Enable plugin loading")
    plugin_dir: str = Field(
        default="plugins",
        description="Plugin directory (relative to project root or absolute)",
    )
    disabled: list[str] = Field(
        default_factory=list,
        description="Plugin names to skip during loading",
    )
    sandbox: bool = Field(
        default=True,
        description="Block dangerous imports in plugins (os, subprocess, etc.)",
    )


class AppSettings(BaseModel):
    """Top-level application settings."""

    debug_mode: bool = Field(default=False, description="Enable debug mode globally")
    workspace_path: Path | None = Field(
        default=None,
        description="Workspace root directory (defaults to cwd)",
    )
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    docker: DockerSettings = Field(default_factory=DockerSettings)
    git: GitSettings = Field(default_factory=GitSettings)
    ui: UISettings = Field(default_factory=UISettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML config file. Requires PyYAML (optional dep)."""
    import yaml

    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return data


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML config file (Python 3.11+ tomllib)."""
    import tomllib

    with open(path, "rb") as f:
        data: dict[str, Any] = tomllib.load(f)
    return data


def load_settings() -> AppSettings:
    """Load settings with the following precedence:

    1. ``.devcommand.yml`` in cwd (project-local)
    2. ``~/.devcommand/config.toml`` (user-global)
    3. Built-in defaults

    Returns:
        Validated :class:`AppSettings` instance.
    """
    # --- project-local YAML -------------------------------------------------
    if _LOCAL_CONFIG_FILE.exists():
        try:
            data = _load_yaml(_LOCAL_CONFIG_FILE)
            logger.info("Loaded project config from %s", _LOCAL_CONFIG_FILE)
            return AppSettings.model_validate(data)
        except ImportError:
            logger.warning(
                "PyYAML is not installed — skipping %s", _LOCAL_CONFIG_FILE
            )
        except Exception:
            logger.warning(
                "Failed to parse %s; falling through", _LOCAL_CONFIG_FILE, exc_info=True
            )

    # --- user-global TOML ---------------------------------------------------
    if _GLOBAL_CONFIG_FILE.exists():
        try:
            data = _load_toml(_GLOBAL_CONFIG_FILE)
            logger.info("Loaded global config from %s", _GLOBAL_CONFIG_FILE)
            return AppSettings.model_validate(data)
        except Exception:
            logger.warning(
                "Failed to parse %s; using defaults",
                _GLOBAL_CONFIG_FILE,
                exc_info=True,
            )

    logger.info("No config file found — using defaults")
    return AppSettings()
