"""Plugins module — dynamic extensions loaded at runtime.

See :mod:`~devcommand.plugins.loader` for discovery/loading and
:mod:`~devcommand.plugins.registry` for lifecycle management.
"""

from devcommand.plugins.loader import PluginLoader, PluginLoadError
from devcommand.plugins.manifest import PluginManifest
from devcommand.plugins.registry import PluginRegistry, PluginState

__all__ = [
    "PluginLoadError",
    "PluginLoader",
    "PluginManifest",
    "PluginRegistry",
    "PluginState",
]
