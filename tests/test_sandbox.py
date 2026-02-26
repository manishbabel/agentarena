"""Tests for sandbox — both git worktree and temp directory modes."""

from pathlib import Path

import pytest
import subprocess

from agentrace.sandbox import (
    create_sandbox,
    cleanup_sandbox,
    is_git_repo,
    list_worktrees,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with one commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    (tmp_path / "hello.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    return tmp_path


@pytest.fixture
def plain_dir(tmp_path: Path) -> Path:
    """Create a plain directory (no git) with some files."""
    (tmp_path / "data.txt").write_text("test data")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.txt").write_text("nested")
    return tmp_path


class TestIsGitRepo:
    def test_git_repo(self, git_repo: Path):
        assert is_git_repo(git_repo) is True

    def test_plain_dir(self, plain_dir: Path):
        assert is_git_repo(plain_dir) is False


# --- Git worktree mode ---


class TestGitWorktreeSandbox:
    def test_creates_worktree(self, git_repo: Path):
        sb = create_sandbox(git_repo)

        assert sb.exists()
        assert (sb / "hello.txt").read_text() == "hello"

        cleanup_sandbox(git_repo, sb)

    def test_worktree_is_isolated(self, git_repo: Path):
        sb = create_sandbox(git_repo)
        (sb / "hello.txt").write_text("modified")

        assert (git_repo / "hello.txt").read_text() == "hello"

        cleanup_sandbox(git_repo, sb)

    def test_multiple_worktrees(self, git_repo: Path):
        sb1 = create_sandbox(git_repo)
        sb2 = create_sandbox(git_repo)

        assert sb1 != sb2
        assert sb1.exists()
        assert sb2.exists()

        cleanup_sandbox(git_repo, sb1)
        cleanup_sandbox(git_repo, sb2)

    def test_cleanup_removes_directory(self, git_repo: Path):
        sb = create_sandbox(git_repo)
        assert sb.exists()

        cleanup_sandbox(git_repo, sb)
        assert not sb.exists()

    def test_list_worktrees(self, git_repo: Path):
        sb = create_sandbox(git_repo)

        trees = list_worktrees(git_repo)
        assert any(str(sb) in t for t in trees)

        cleanup_sandbox(git_repo, sb)


# --- Temp directory mode (non-git) ---


class TestTempDirSandbox:
    def test_creates_copy(self, plain_dir: Path):
        sb = create_sandbox(plain_dir)

        assert sb.exists()
        assert (sb / "data.txt").read_text() == "test data"
        assert (sb / "subdir" / "nested.txt").read_text() == "nested"

        cleanup_sandbox(plain_dir, sb)

    def test_copy_is_isolated(self, plain_dir: Path):
        sb = create_sandbox(plain_dir)
        (sb / "data.txt").write_text("modified")

        assert (plain_dir / "data.txt").read_text() == "test data"

        cleanup_sandbox(plain_dir, sb)

    def test_cleanup_removes_directory(self, plain_dir: Path):
        sb = create_sandbox(plain_dir)
        assert sb.exists()

        cleanup_sandbox(plain_dir, sb)
        assert not sb.exists()

    def test_cleanup_nonexistent_is_noop(self, plain_dir: Path):
        fake = plain_dir / ".agentrace" / "worktrees" / "run-fake"
        cleanup_sandbox(plain_dir, fake)  # should not raise
