"""Pydantic models for Git repository entities."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    """Summary of a single git commit."""

    sha: str = Field(description="Full commit SHA")
    short_sha: str = Field(description="Short SHA (first 8 chars)")
    message: str = Field(description="Commit message (first line)")
    author: str = Field(description="Author name")
    timestamp: datetime = Field(description="Commit timestamp")


class BranchInfo(BaseModel):
    """Summary of a git branch."""

    name: str = Field(description="Branch name")
    is_active: bool = Field(default=False, description="Whether this is the checked-out branch")
    tracking: str | None = Field(
        default=None, description="Remote tracking branch (e.g. origin/main)"
    )


class FileChange(BaseModel):
    """A single changed file in the working tree."""

    path: str = Field(description="Relative file path")
    change_type: str = Field(description="Change type: A/M/D/R/U")


class GitStatus(BaseModel):
    """Git repository status snapshot."""

    available: bool = Field(description="Whether a git repo was found")
    branch: str | None = Field(default=None, description="Current branch name")
    is_dirty: bool = Field(default=False, description="Uncommitted changes exist")
    untracked_files: list[str] = Field(default_factory=list, description="Untracked file paths")
    staged_files: list[FileChange] = Field(default_factory=list, description="Staged changes")
    modified_files: list[FileChange] = Field(default_factory=list, description="Unstaged changes")
    head_commit: CommitInfo | None = Field(default=None, description="HEAD commit info")
    recent_commits: list[CommitInfo] = Field(
        default_factory=list, description="Recent commits (last N)"
    )
    stash_count: int = Field(ge=0, default=0, description="Number of stashed entries")
    timestamp: datetime = Field(default_factory=datetime.now)
