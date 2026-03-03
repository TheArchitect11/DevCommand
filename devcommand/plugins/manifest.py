"""Plugin manifest model — parsed from ``manifest.yaml``.

Every plugin directory must contain a ``manifest.yaml`` that declares
metadata, entry point, capabilities, and dependency requirements.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class PluginCapabilities(BaseModel):
    """What the plugin provides."""

    panels: list[str] = Field(
        default_factory=list,
        description="Panel class names exported by this plugin",
    )
    services: list[str] = Field(
        default_factory=list,
        description="Service class names exported by this plugin",
    )
    event_handlers: list[str] = Field(
        default_factory=list,
        description="Event handler names to auto-register on the EventBus",
    )


class PluginManifest(BaseModel):
    """Schema for ``manifest.yaml`` inside each plugin directory."""

    name: str = Field(min_length=1, max_length=64, description="Plugin identifier (slug)")
    version: str = Field(default="0.1.0", description="Semver version string")
    description: str = Field(default="", max_length=256)
    author: str = Field(default="")
    entry_point: str = Field(
        description="Dotted import path relative to plugin dir, e.g. 'plugin:MyPlugin'",
    )
    min_app_version: str = Field(
        default="0.1.0",
        description="Minimum DevCommand version required",
    )
    capabilities: PluginCapabilities = Field(default_factory=PluginCapabilities)
    dependencies: list[str] = Field(
        default_factory=list,
        description="Python package names required (checked but not auto-installed)",
    )

    # Set during loading — not part of the YAML
    plugin_dir: Path | None = Field(default=None, exclude=True)

    @property
    def module_path(self) -> str:
        """Module part of entry_point (before the colon)."""
        return self.entry_point.split(":")[0]

    @property
    def class_name(self) -> str:
        """Class part of entry_point (after the colon)."""
        parts = self.entry_point.split(":")
        return parts[1] if len(parts) > 1 else parts[0]
