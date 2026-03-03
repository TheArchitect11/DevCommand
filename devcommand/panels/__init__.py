"""Panels module — reactive TUI panel components.

All panels subscribe to ``AppState`` reactive fields and render
via Rich renderables.  No panel makes direct external calls.
"""

from devcommand.panels.docker_panel import DockerPanel
from devcommand.panels.git_panel import GitPanel
from devcommand.panels.server_panel import ServerPanel
from devcommand.panels.system_panel import SystemPanel
from devcommand.panels.todo_panel import TodoPanel

__all__ = [
    "DockerPanel",
    "GitPanel",
    "ServerPanel",
    "SystemPanel",
    "TodoPanel",
]
