"""Tests for the plugin system — loader, manifest, and registry."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from devcommand.core.base_plugin import BasePlugin
from devcommand.core.event_bus import EventBus
from devcommand.plugins.loader import PluginLoader, PluginLoadError
from devcommand.plugins.manifest import PluginManifest
from devcommand.plugins.registry import PluginRegistry, PluginState


class TestPluginManifest:
    """Tests for PluginManifest model."""

    def test_valid_manifest(self) -> None:
        m = PluginManifest(name="test", entry_point="plugin:TestPlugin")
        assert m.name == "test"
        assert m.module_path == "plugin"
        assert m.class_name == "TestPlugin"

    def test_entry_point_without_colon(self) -> None:
        m = PluginManifest(name="test", entry_point="my_module")
        assert m.module_path == "my_module"
        assert m.class_name == "my_module"

    def test_capabilities_default(self) -> None:
        m = PluginManifest(name="test", entry_point="p:C")
        assert m.capabilities.panels == []
        assert m.capabilities.services == []


class TestPluginLoader:
    """Tests for PluginLoader discover_and_load."""

    def test_nonexistent_dir(self) -> None:
        loader = PluginLoader(plugin_dir=Path("/nonexistent"))
        result = loader.discover_and_load()
        assert result == []

    def test_load_hello_world(self) -> None:
        loader = PluginLoader(
            plugin_dir=Path("devcommand/plugins"),
            sandbox=True,
        )
        plugins = loader.discover_and_load()
        assert len(plugins) >= 1
        names = [p.name for p in plugins]
        assert "hello_world" in names

    def test_disabled_skipped(self) -> None:
        loader = PluginLoader(
            plugin_dir=Path("devcommand/plugins"),
            disabled={"hello_world"},
        )
        plugins = loader.discover_and_load()
        assert all(p.name != "hello_world" for p in plugins)

    def test_sandbox_blocks_os(self, tmp_path: Path) -> None:
        """Plugin that imports os should be blocked."""
        mal = tmp_path / "bad_plugin"
        mal.mkdir()
        (mal / "manifest.yaml").write_text(
            'name: bad\nentry_point: "plugin:Bad"\n'
        )
        (mal / "plugin.py").write_text(
            "import os\n"
            "from devcommand.core.base_plugin import BasePlugin\n"
            "class Bad(BasePlugin):\n"
            "  async def activate(self, eb, st): pass\n"
            "  async def deactivate(self): pass\n"
        )
        loader = PluginLoader(plugin_dir=tmp_path, sandbox=True)
        result = loader.discover_and_load()
        assert len(result) == 0
        assert "bad" in loader.errors


class TestPluginRegistry:
    """Tests for PluginRegistry lifecycle."""

    @pytest.mark.asyncio
    async def test_activate_deactivate(self) -> None:
        loader = PluginLoader(plugin_dir=Path("devcommand/plugins"))
        plugins = loader.discover_and_load()

        reg = PluginRegistry()
        reg.register_many(plugins)
        assert len(reg) >= 1

        await reg.activate_all(EventBus(), None)  # type: ignore
        assert len(reg.active_plugins) >= 1

        await reg.deactivate_all()
        assert len(reg.active_plugins) == 0

    @pytest.mark.asyncio
    async def test_failed_plugin_tracked(self) -> None:
        """Plugin that throws on activate should be marked FAILED."""

        class BrokenPlugin(BasePlugin):
            async def activate(self, eb, st) -> None:  # type: ignore
                raise RuntimeError("broke")

            async def deactivate(self) -> None:
                pass

        reg = PluginRegistry()
        reg.register(BrokenPlugin())
        await reg.activate_all(EventBus(), None)  # type: ignore
        assert len(reg.failed_plugins) == 1
