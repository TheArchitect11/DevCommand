"""CLI argument parser for DevCommand.

Parses ``--version``, ``--workspace``, ``--refresh``, ``--debug``,
``--no-plugins``, and ``--profile`` flags.

Returns a typed :class:`CLIArgs` dataclass.  CLI validation is
designed to be self-contained — it does **not** start Textual.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from devcommand.__version__ import __version__


@dataclass(frozen=True)
class CLIArgs:
    """Parsed and validated CLI arguments."""

    workspace: Path
    refresh: float | None
    debug: bool
    no_plugins: bool
    profile: bool
    config: Path | None


def parse_args(argv: list[str] | None = None) -> CLIArgs:
    """Parse CLI arguments and return a validated :class:`CLIArgs`.

    When ``--version`` is passed, prints the version and exits.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).
    """
    parser = argparse.ArgumentParser(
        prog="devcmd",
        description="DevCommand — Developer Command Center TUI",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"DevCommand {__version__}",
    )
    parser.add_argument(
        "-w", "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace root directory (default: cwd)",
    )
    parser.add_argument(
        "-r", "--refresh",
        type=float,
        default=None,
        metavar="SECS",
        help="Override scheduler tick interval (seconds)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug logging (verbose console + DEBUG level)",
    )
    parser.add_argument(
        "--no-plugins",
        action="store_true",
        default=False,
        help="Disable plugin loading",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        default=False,
        help="Enable performance profiling (dump report on exit)",
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to config file (.yml or .toml)",
    )

    ns = parser.parse_args(argv)

    # Validate workspace exists
    workspace: Path = ns.workspace.resolve()
    if not workspace.is_dir():
        parser.error(f"Workspace directory does not exist: {workspace}")

    # Validate refresh bounds
    if ns.refresh is not None and not (0.25 <= ns.refresh <= 60.0):
        parser.error(f"--refresh must be between 0.25 and 60.0 (got {ns.refresh})")

    # Validate config path if provided
    if ns.config is not None and not ns.config.exists():
        parser.error(f"Config file does not exist: {ns.config}")

    return CLIArgs(
        workspace=workspace,
        refresh=ns.refresh,
        debug=ns.debug,
        no_plugins=ns.no_plugins,
        profile=ns.profile,
        config=ns.config,
    )
