"""Git repository service using GitPython.

Inspects the repository at a given path for branch info, status,
staged/modified files, recent commits, and stash count.  All
blocking GitPython calls are dispatched to a thread-pool executor.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from devcommand.core.base_service import BaseService
from devcommand.models.git import CommitInfo, FileChange, GitStatus
from devcommand.utils.cache import TTLCache

logger = logging.getLogger(__name__)


class GitService(BaseService):
    """Async Git service backed by GitPython.

    Gracefully returns ``GitStatus(available=False)`` when no repo
    is found at the configured path.

    Usage::

        service = GitService(repo_path=Path("."), cache_ttl=3.0)
        await service.start()
        status = await service.get_status()
    """

    def __init__(
        self,
        repo_path: Path | None = None,
        cache_ttl: float = 3.0,
        recent_commit_count: int = 10,
    ) -> None:
        super().__init__()
        self._repo_path = repo_path or Path.cwd()
        self._cache: TTLCache[GitStatus] = TTLCache(ttl=cache_ttl)
        self._recent_n = recent_commit_count
        self._repo: Any = None  # git.Repo | None

    async def start(self) -> None:
        """Open the git repository (best-effort)."""
        await super().start()
        loop = asyncio.get_running_loop()
        try:
            from git import Repo

            self._repo = await loop.run_in_executor(
                None, Repo, str(self._repo_path)
            )
            logger.info("Opened git repo at %s", self._repo_path)
        except Exception:
            logger.warning("No valid git repo at %s", self._repo_path, exc_info=True)
            self._repo = None

    async def stop(self) -> None:
        """Release repo handle and clear cache."""
        self._repo = None
        self._cache.clear()
        await super().stop()

    # -- public API ---------------------------------------------------------

    async def get_status(self) -> GitStatus:
        """Return repository status (cached)."""
        cached = self._cache.get("status")
        if cached is not None:
            return cached

        if self._repo is None:
            return GitStatus(available=False)

        loop = asyncio.get_running_loop()
        try:
            status = await loop.run_in_executor(None, self._collect_status)
        except Exception:
            logger.exception("Error collecting git status")
            return GitStatus(available=False)

        self._cache.set("status", status)
        return status

    async def invalidate(self) -> None:
        """Force next call to re-read from disk."""
        self._cache.invalidate("status")

    @property
    def is_available(self) -> bool:
        """Whether a valid repo is open."""
        return self._repo is not None

    # -- private (sync, runs in executor) -----------------------------------

    def _collect_status(self) -> GitStatus:
        """Synchronous git data collection."""
        repo = self._repo
        assert repo is not None

        # Branch
        try:
            branch_name = str(repo.active_branch)
        except TypeError:
            branch_name = "HEAD (detached)"

        # Staged files
        staged: list[FileChange] = []
        try:
            for diff in repo.index.diff("HEAD"):
                staged.append(
                    FileChange(
                        path=diff.a_path or diff.b_path or "",
                        change_type=diff.change_type or "M",
                    )
                )
        except Exception:
            pass  # empty repo / no HEAD

        # Modified (unstaged) files
        modified: list[FileChange] = []
        try:
            for diff in repo.index.diff(None):
                modified.append(
                    FileChange(
                        path=diff.a_path or diff.b_path or "",
                        change_type=diff.change_type or "M",
                    )
                )
        except Exception:
            pass

        # HEAD commit
        head_commit: CommitInfo | None = None
        try:
            hc = repo.head.commit
            head_commit = self._commit_to_model(hc)
        except Exception:
            pass

        # Recent commits
        recent: list[CommitInfo] = []
        try:
            for c in repo.iter_commits(max_count=self._recent_n):
                recent.append(self._commit_to_model(c))
        except Exception:
            pass

        # Stash count
        stash_count = 0
        import contextlib
        with contextlib.suppress(Exception):
            stash_count = len(list(repo.git.stash("list").splitlines()))

        return GitStatus(
            available=True,
            branch=branch_name,
            is_dirty=repo.is_dirty(untracked_files=True),
            untracked_files=repo.untracked_files,
            staged_files=staged,
            modified_files=modified,
            head_commit=head_commit,
            recent_commits=recent,
            stash_count=stash_count,
            timestamp=datetime.now(),
        )

    @staticmethod
    def _commit_to_model(commit: Any) -> CommitInfo:
        """Convert a ``git.Commit`` to our Pydantic model."""
        return CommitInfo(
            sha=str(commit.hexsha),
            short_sha=str(commit.hexsha)[:8],
            message=commit.message.strip().split("\n")[0],
            author=str(commit.author),
            timestamp=datetime.fromtimestamp(
                commit.committed_date, tz=UTC
            ),
        )
