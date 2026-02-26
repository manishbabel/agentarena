"""Tests for the validation runner."""

from pathlib import Path

import pytest

from agentarena.validator import run_validation


class TestRunValidation:
    def test_passing_command(self, tmp_path: Path):
        result = run_validation("echo hello", cwd=tmp_path)

        assert result.passed is True
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.duration_seconds >= 0
        assert result.timed_out is False

    def test_failing_command(self, tmp_path: Path):
        result = run_validation("exit 1", cwd=tmp_path)

        assert result.passed is False
        assert result.exit_code == 1
        assert result.timed_out is False

    def test_command_with_stderr(self, tmp_path: Path):
        result = run_validation("echo err >&2 && exit 2", cwd=tmp_path)

        assert result.passed is False
        assert result.exit_code == 2
        assert "err" in result.stderr

    def test_timeout(self, tmp_path: Path):
        result = run_validation("sleep 10", cwd=tmp_path, timeout=1)

        assert result.passed is False
        assert result.timed_out is True
        assert result.exit_code == -1
        assert "timed out" in result.stderr

    def test_runs_in_correct_directory(self, tmp_path: Path):
        (tmp_path / "marker.txt").write_text("found")
        result = run_validation("cat marker.txt", cwd=tmp_path)

        assert result.passed is True
        assert "found" in result.stdout

    def test_nonexistent_command(self, tmp_path: Path):
        result = run_validation("nonexistent_command_xyz", cwd=tmp_path)

        assert result.passed is False
        assert result.exit_code != 0
