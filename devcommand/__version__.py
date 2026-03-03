"""Single source of truth for the DevCommand version.

Referenced by ``pyproject.toml`` (via hatch-vcs or manual sync),
``devcommand/__init__.py``, and the ``--version`` CLI flag.
"""

__version__: str = "0.1.0"
