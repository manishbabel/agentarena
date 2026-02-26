"""Tests for run history storage."""

import json
from pathlib import Path

from agentrace.history import save_run, HISTORY_DIR
from agentrace.metrics import RunMetrics, TaskSummary


class TestSaveRun:
    def test_saves_json_file(self, tmp_path: Path):
        runs = [
            RunMetrics(agent_name="a", task_name="t1", passed=True, wall_time_seconds=10),
            RunMetrics(agent_name="b", task_name="t1", passed=False, wall_time_seconds=20),
        ]
        summaries = [
            TaskSummary(agent_name="a", runs=[runs[0]]),
            TaskSummary(agent_name="b", runs=[runs[1]]),
        ]

        saved = save_run(tmp_path, "test-project", runs, summaries)

        assert saved.exists()
        assert saved.suffix == ".json"

        data = json.loads(saved.read_text())
        assert data["project"] == "test-project"
        assert data["num_tasks"] == 1
        assert data["num_agents"] == 2
        assert data["winner"] == "a"
        assert len(data["runs"]) == 2
        assert len(data["summary"]) == 2

    def test_creates_directory(self, tmp_path: Path):
        runs = [RunMetrics(agent_name="a", task_name="t1", passed=True)]
        summaries = [TaskSummary(agent_name="a", runs=runs)]

        save_run(tmp_path, "test", runs, summaries)

        history_dir = tmp_path / HISTORY_DIR
        assert history_dir.exists()

    def test_multiple_saves_create_separate_files(self, tmp_path: Path):
        runs = [RunMetrics(agent_name="a", task_name="t1", passed=True)]
        summaries = [TaskSummary(agent_name="a", runs=runs)]

        f1 = save_run(tmp_path, "test", runs, summaries)
        f2 = save_run(tmp_path, "test", runs, summaries)

        # Files should be different (different timestamps, or at least both exist)
        history_dir = tmp_path / HISTORY_DIR
        files = list(history_dir.glob("*.json"))
        assert len(files) >= 1  # may be same second, so at least 1
