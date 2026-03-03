"""UI panels module — placeholder panels for the DevCommand TUI."""

from devcommand.ui.panels.docker_panel import DockerPanel
from devcommand.ui.panels.git_panel import GitPanel
from devcommand.ui.panels.logs_panel import LogsPanel, StateLogHandler
from devcommand.ui.panels.server_panel import ServerPanel
from devcommand.ui.panels.system_panel import SystemPanel
from devcommand.ui.panels.todo_panel import TodoPanel

__all__ = [
    "DockerPanel",
    "GitPanel",
    "LogsPanel",
    "ServerPanel",
    "StateLogHandler",
    "SystemPanel",
    "TodoPanel",
]
