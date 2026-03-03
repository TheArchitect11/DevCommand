"""Services module — async background services.

All services inherit from :class:`~devcommand.core.base_service.BaseService`
and follow these conventions:

- Independent of the UI layer
- All external I/O dispatched to a thread-pool executor
- Return structured Pydantic models
- Per-service :class:`~devcommand.utils.cache.TTLCache`
- Graceful degradation on failure
"""

from devcommand.services.docker_service import DockerService
from devcommand.services.git_service import GitService
from devcommand.services.health_service import ServerHealthService
from devcommand.services.system_service import SystemService
from devcommand.services.todo_service import TodoService

__all__ = [
    "DockerService",
    "GitService",
    "ServerHealthService",
    "SystemService",
    "TodoService",
]
