"""Plugin loader — discovers, validates, and imports plugins safely.

The loader scans a directory for subdirectories containing a
``manifest.yaml``, validates the manifest, checks dependencies,
and dynamically imports the plugin class in a sandboxed fashion.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from devcommand.core.base_plugin import BasePlugin
from devcommand.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)

# Modules that plugins are NOT allowed to import directly
_BLOCKED_MODULES: frozenset[str] = frozenset({
    "os",       # prevent shell commands — plugins should use services
    "shutil",   # prevent file ops outside sandbox
    "ctypes",
    "subprocess",
})


class PluginLoadError(Exception):
    """Raised when a plugin fails to load."""

    def __init__(self, plugin_name: str, reason: str) -> None:
        self.plugin_name = plugin_name
        self.reason = reason
        super().__init__(f"Plugin '{plugin_name}': {reason}")


class PluginLoader:
    """Discovers and loads plugins from a directory.

    Usage::

        loader = PluginLoader(Path("plugins/"), disabled={"broken_plugin"})
        plugins = loader.discover_and_load()
    """

    def __init__(
        self,
        plugin_dir: Path,
        disabled: set[str] | None = None,
        sandbox: bool = True,
    ) -> None:
        self._plugin_dir = plugin_dir
        self._disabled = disabled or set()
        self._sandbox = sandbox
        self._loaded: dict[str, BasePlugin] = {}
        self._errors: dict[str, str] = {}

    # -- public API ---------------------------------------------------------

    def discover_and_load(self) -> list[BasePlugin]:
        """Scan the plugin directory and return successfully loaded plugins.

        Each subdirectory with a valid ``manifest.yaml`` is treated as
        a plugin candidate.  Disabled, invalid, or failing plugins are
        logged and skipped — they never crash the app.
        """
        if not self._plugin_dir.is_dir():
            logger.info("Plugin directory does not exist: %s", self._plugin_dir)
            return []

        plugins: list[BasePlugin] = []

        for child in sorted(self._plugin_dir.iterdir()):
            if not child.is_dir() or child.name.startswith(("_", ".")):
                continue

            manifest_path = child / "manifest.yaml"
            if not manifest_path.exists():
                logger.debug("Skipping %s (no manifest.yaml)", child.name)
                continue

            try:
                plugin = self._load_one(child, manifest_path)
                if plugin is not None:
                    plugins.append(plugin)
            except PluginLoadError as exc:
                self._errors[exc.plugin_name] = exc.reason
                logger.warning("Plugin load failed: %s", exc)
            except Exception as exc:
                self._errors[child.name] = str(exc)
                logger.exception("Unexpected error loading plugin %s", child.name)

        logger.info(
            "Plugin discovery: %d loaded, %d failed, %d disabled",
            len(plugins),
            len(self._errors),
            len(self._disabled),
        )
        return plugins

    @property
    def errors(self) -> dict[str, str]:
        """Plugin name → error message for any that failed to load."""
        return dict(self._errors)

    # -- internals ----------------------------------------------------------

    def _load_one(self, plugin_dir: Path, manifest_path: Path) -> BasePlugin | None:
        """Load a single plugin from its directory."""
        # 1. Parse manifest
        manifest = self._parse_manifest(plugin_dir, manifest_path)

        # 2. Check disabled
        if manifest.name in self._disabled:
            logger.info("Plugin '%s' is disabled via config — skipping", manifest.name)
            return None

        # 3. Check dependencies
        self._check_dependencies(manifest)

        # 4. Import module safely
        module = self._import_module(manifest, plugin_dir)

        # 5. Instantiate plugin class
        plugin = self._instantiate(manifest, module)

        self._loaded[manifest.name] = plugin
        logger.info(
            "Loaded plugin '%s' v%s from %s",
            manifest.name,
            manifest.version,
            plugin_dir,
        )
        return plugin

    def _parse_manifest(self, plugin_dir: Path, manifest_path: Path) -> PluginManifest:
        """Parse and validate manifest.yaml."""
        import yaml

        try:
            raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            raise PluginLoadError(plugin_dir.name, f"Invalid YAML: {exc}") from exc

        try:
            manifest = PluginManifest.model_validate(raw)
            manifest.plugin_dir = plugin_dir
            return manifest
        except Exception as exc:
            raise PluginLoadError(
                raw.get("name", plugin_dir.name),
                f"Manifest validation failed: {exc}",
            ) from exc

    def _check_dependencies(self, manifest: PluginManifest) -> None:
        """Verify that all declared dependencies are importable."""
        missing: list[str] = []
        for dep in manifest.dependencies:
            dep_name = dep.split(">=")[0].split("==")[0].strip()
            if importlib.util.find_spec(dep_name) is None:
                missing.append(dep_name)
        if missing:
            raise PluginLoadError(
                manifest.name,
                f"Missing dependencies: {', '.join(missing)}",
            )

    def _import_module(self, manifest: PluginManifest, plugin_dir: Path) -> ModuleType:
        """Dynamically import the plugin module with optional sandboxing.

        When sandboxing is enabled, the source is scanned with
        :func:`_audit_source` **before** execution.  This catches
        blocked imports even for modules already cached in ``sys.modules``.
        """
        module_file = plugin_dir / manifest.module_path.replace(".", "/")

        # Try as package (__init__.py) or single file (.py)
        if module_file.is_dir():
            module_file = module_file / "__init__.py"
        elif not module_file.suffix:
            module_file = module_file.with_suffix(".py")

        if not module_file.exists():
            raise PluginLoadError(
                manifest.name,
                f"Entry point module not found: {module_file}",
            )

        # Sandbox: static analysis of source before execution
        if self._sandbox:
            _audit_source(manifest.name, module_file, _BLOCKED_MODULES)

        # Construct a namespaced module name to avoid collisions
        full_module_name = f"devcommand.plugins._loaded.{manifest.name}"

        try:
            spec = importlib.util.spec_from_file_location(
                full_module_name, module_file
            )
            if spec is None or spec.loader is None:
                raise PluginLoadError(manifest.name, f"Cannot create module spec for {module_file}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[full_module_name] = module
            spec.loader.exec_module(module)
            return module
        except PluginLoadError:
            raise
        except Exception as exc:
            raise PluginLoadError(
                manifest.name, f"Import failed: {exc}"
            ) from exc

    def _instantiate(self, manifest: PluginManifest, module: ModuleType) -> BasePlugin:
        """Instantiate the plugin class from the loaded module."""
        class_name = manifest.class_name
        cls: Any = getattr(module, class_name, None)

        if cls is None:
            raise PluginLoadError(
                manifest.name,
                f"Class '{class_name}' not found in module",
            )

        if not (isinstance(cls, type) and issubclass(cls, BasePlugin)):
            raise PluginLoadError(
                manifest.name,
                f"'{class_name}' is not a subclass of BasePlugin",
            )

        try:
            return cls(manifest=manifest)
        except Exception as exc:
            raise PluginLoadError(
                manifest.name, f"Instantiation failed: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# AST-based import sandboxing
# ---------------------------------------------------------------------------

def _audit_source(
    plugin_name: str,
    source_path: Path,
    blocked: frozenset[str],
) -> None:
    """Parse plugin source and reject any import of a blocked module.

    Uses :mod:`ast` to statically analyse ``import X`` and
    ``from X import …`` statements **before** executing any code.
    This is more robust than a meta-path finder because it catches
    imports of modules already cached in ``sys.modules``.
    """
    import ast

    source = source_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(source_path))
    except SyntaxError as exc:
        raise PluginLoadError(plugin_name, f"Syntax error in {source_path}: {exc}") from exc

    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in blocked:
                    violations.append(
                        f"line {node.lineno}: import {alias.name}"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in blocked:
                    violations.append(
                        f"line {node.lineno}: from {node.module} import …"
                    )

    if violations:
        detail = "; ".join(violations)
        raise PluginLoadError(
            plugin_name,
            f"Blocked import(s) detected — {detail}. "
            f"Plugins may not import: {', '.join(sorted(blocked))}",
        )
