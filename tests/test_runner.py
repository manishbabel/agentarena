"""Tests for the core benchmark runner."""

from pathlib import Path

import subprocess
import pytest

from agentarena.config import AgentConfig, BenchConfig, TaskConfig
from agentarena.runner import run_benchmark, _run_single, _build_agent


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo so sandbox works."""
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
    """Non-git directory for domain agent tests."""
    (tmp_path / "data.txt").write_text("test data")
    return tmp_path


def _make_config(
    tasks: list[dict],
    agents: list[dict],
    project: str = "test-project",
) -> BenchConfig:
    """Helper to build a BenchConfig from dicts."""
    return BenchConfig(
        project=project,
        timeout=30,
        tasks=[TaskConfig(**t) for t in tasks],
        agents=[AgentConfig(**a) for a in agents],
    )


class TestRunSingle:
    def test_passing_run(self, git_repo: Path):
        """Agent succeeds, validation passes."""
        agent = _build_agent(AgentConfig(
            name="echo-agent",
            command="echo 'done' # {prompt}",
        ))
        task = TaskConfig(name="t1", prompt="do something", validate_command="exit 0")

        result = _run_single(agent, task, git_repo, global_timeout=30, base_ref="HEAD")

        assert result.passed is True
        assert result.wall_time_seconds >= 0
        assert result.timed_out is False
        assert result.error is None

    def test_agent_succeeds_validation_fails(self, git_repo: Path):
        """Agent runs fine but validation fails (code didn't work)."""
        agent = _build_agent(AgentConfig(
            name="echo-agent",
            command="echo 'done' # {prompt}",
        ))
        task = TaskConfig(name="t1", prompt="do something", validate_command="exit 1")

        result = _run_single(agent, task, git_repo, global_timeout=30, base_ref="HEAD")

        assert result.passed is False
        assert result.timed_out is False

    def test_agent_times_out(self, git_repo: Path):
        """Agent takes too long."""
        agent = _build_agent(AgentConfig(
            name="slow-agent",
            command="sleep 10 # {prompt}",
        ))
        task = TaskConfig(name="t1", prompt="do something", validate_command="exit 0", timeout=1)

        result = _run_single(agent, task, git_repo, global_timeout=30, base_ref="HEAD")

        assert result.passed is False
        assert result.timed_out is True

    def test_sandbox_is_cleaned_up(self, git_repo: Path):
        """Sandbox directory should be removed after run."""
        agent = _build_agent(AgentConfig(
            name="echo-agent",
            command="echo 'done' # {prompt}",
        ))
        task = TaskConfig(name="t1", prompt="test", validate_command="exit 0")

        _run_single(agent, task, git_repo, global_timeout=30, base_ref="HEAD")

        # Check no leftover worktrees
        worktree_dir = git_repo / ".agentarena" / "worktrees"
        if worktree_dir.exists():
            remaining = list(worktree_dir.iterdir())
            assert len(remaining) == 0

    def test_works_with_plain_directory(self, plain_dir: Path):
        """Non-git project uses temp dir sandbox."""
        agent = _build_agent(AgentConfig(
            name="echo-agent",
            command="echo 'done' # {prompt}",
        ))
        task = TaskConfig(name="t1", prompt="test", validate_command="exit 0")

        result = _run_single(agent, task, plain_dir, global_timeout=30, base_ref="HEAD")

        assert result.passed is True


class TestRunBenchmark:
    def test_full_run(self, git_repo: Path):
        """Run 2 tasks × 2 agents = 4 results."""
        config = _make_config(
            tasks=[
                {"name": "t1", "prompt": "task one", "validate": "exit 0"},
                {"name": "t2", "prompt": "task two", "validate": "exit 0"},
            ],
            agents=[
                {"name": "agent-a", "command": "echo 'a' # {prompt}"},
                {"name": "agent-b", "command": "echo 'b' # {prompt}"},
            ],
        )

        results = run_benchmark(config, git_repo)

        assert len(results) == 4
        assert all(r.passed for r in results)

        # Check all combos present
        combos = {(r.agent_name, r.task_name) for r in results}
        assert combos == {
            ("agent-a", "t1"), ("agent-a", "t2"),
            ("agent-b", "t1"), ("agent-b", "t2"),
        }

    def test_mixed_pass_fail(self, git_repo: Path):
        """One task passes validation, one fails."""
        config = _make_config(
            tasks=[
                {"name": "pass-task", "prompt": "p", "validate": "exit 0"},
                {"name": "fail-task", "prompt": "p", "validate": "exit 1"},
            ],
            agents=[
                {"name": "agent-a", "command": "echo 'a' # {prompt}"},
            ],
        )

        results = run_benchmark(config, git_repo)

        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]
        assert len(passed) == 1
        assert len(failed) == 1
        assert passed[0].task_name == "pass-task"
        assert failed[0].task_name == "fail-task"
