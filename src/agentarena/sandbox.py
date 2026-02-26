"""Sandbox for isolated agent runs.

Two modes:
  - Git repo → uses git worktree (lightweight checkout, shares history)
  - Non-git  → uses temp directory with file copies

Either way, every agent gets a clean, isolated workspace.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path


WORKTREE_DIR = ".agentarena/worktrees"


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def is_git_repo(path: Path) -> bool:
    """Check if the path is inside a git repository."""
    try:
        _run_git(["rev-parse", "--git-dir"], cwd=path)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_sandbox(project_path: Path, ref: str = "HEAD") -> Path:
    """Create an isolated workspace for an agent run.

    Automatically picks the right strategy:
      - Git repo → git worktree (fast, lightweight)
      - Not a git repo → temp directory copy (works anywhere)

    Args:
        project_path: Root of the project.
        ref: Git ref to check out (only used for git repos).

    Returns:
        Path to the isolated workspace.
    """
    if is_git_repo(project_path):
        return _create_worktree(project_path, ref)
    else:
        return _create_temp_copy(project_path)


def cleanup_sandbox(project_path: Path, sandbox_path: Path) -> None:
    """Remove a sandbox (worktree or temp directory).

    Args:
        project_path: Root of the project.
        sandbox_path: Path to the sandbox to remove.
    """
    if not sandbox_path.exists():
        return

    if is_git_repo(project_path):
        _cleanup_worktree(project_path, sandbox_path)
    else:
        _cleanup_temp_copy(sandbox_path)


# --- Git worktree strategy ---


def _create_worktree(repo_path: Path, ref: str = "HEAD") -> Path:
    """Create a git worktree for isolated runs."""
    run_id = uuid.uuid4().hex[:12]
    worktree_path = repo_path / WORKTREE_DIR / f"run-{run_id}"
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        _run_git(
            ["worktree", "add", str(worktree_path), "--detach", ref],
            cwd=repo_path,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to create worktree at {worktree_path}: {e.stderr.strip()}"
        ) from e

    return worktree_path


def _cleanup_worktree(repo_path: Path, worktree_path: Path) -> None:
    """Remove a git worktree."""
    try:
        _run_git(
            ["worktree", "remove", str(worktree_path), "--force"],
            cwd=repo_path,
        )
    except subprocess.CalledProcessError:
        _run_git(["worktree", "prune"], cwd=repo_path)


# --- Temp directory strategy (non-git) ---


def _create_temp_copy(project_path: Path) -> Path:
    """Create a temp directory with a copy of project files."""
    run_id = uuid.uuid4().hex[:12]
    sandbox_dir = project_path / WORKTREE_DIR
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    sandbox_path = sandbox_dir / f"run-{run_id}"

    shutil.copytree(
        project_path,
        sandbox_path,
        ignore=shutil.ignore_patterns(
            ".git", ".agentarena", ".venv", "venv", "__pycache__", "node_modules",
        ),
    )

    return sandbox_path


def _cleanup_temp_copy(sandbox_path: Path) -> None:
    """Remove a temp directory sandbox."""
    shutil.rmtree(sandbox_path, ignore_errors=True)


# --- Utilities ---


def list_worktrees(repo_path: Path) -> list[str]:
    """List all active git worktrees (for debugging/cleanup)."""
    result = _run_git(["worktree", "list", "--porcelain"], cwd=repo_path)
    return [
        line.split(" ", 1)[1]
        for line in result.stdout.splitlines()
        if line.startswith("worktree ")
    ]
