"""Tests for bench.yaml config parsing and validation."""

from pathlib import Path

import pytest

from agentarena.config import (
    AgentConfig,
    BenchConfig,
    TaskConfig,
    load_config,
    parse_agent_flag,
)

VALID_YAML = """\
project: my-app
base: HEAD
timeout: 120

tasks:
  - name: fix-bug
    prompt: "Fix the bug in main.py"
    validate: "pytest tests/"

  - name: add-feature
    prompt: "Add logging to the API"
    validate: "python -m pytest"
    timeout: 300

agents:
  - name: claude-code
    command: "claude --print '{prompt}'"

  - name: aider
    command: "aider --message '{prompt}' --yes-always"
"""


class TestBenchConfig:
    def test_valid_config(self, tmp_path: Path):
        f = tmp_path / "bench.yaml"
        f.write_text(VALID_YAML)
        cfg = load_config(f)

        assert cfg.project == "my-app"
        assert cfg.base == "HEAD"
        assert cfg.timeout == 120
        assert len(cfg.tasks) == 2
        assert len(cfg.agents) == 2

    def test_defaults(self, tmp_path: Path):
        minimal = """\
tasks:
  - name: t1
    prompt: "do something"
    validate: "echo ok"
agents:
  - name: a1
    command: "agent '{prompt}'"
"""
        f = tmp_path / "bench.yaml"
        f.write_text(minimal)
        cfg = load_config(f)

        assert cfg.project == "default"
        assert cfg.base == "HEAD"
        assert cfg.timeout == 120

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nope.yaml")

    def test_invalid_yaml_not_dict(self, tmp_path: Path):
        f = tmp_path / "bench.yaml"
        f.write_text("- just a list")
        with pytest.raises(ValueError, match="expected a YAML mapping"):
            load_config(f)

    def test_no_tasks_fails(self, tmp_path: Path):
        f = tmp_path / "bench.yaml"
        f.write_text("tasks: []\nagents:\n  - name: a1\n    command: \"x '{prompt}'\"")
        with pytest.raises(Exception):
            load_config(f)

    def test_no_agents_fails(self, tmp_path: Path):
        f = tmp_path / "bench.yaml"
        f.write_text("tasks:\n  - name: t1\n    prompt: p\n    validate: v\nagents: []")
        with pytest.raises(Exception):
            load_config(f)

    def test_duplicate_task_names(self, tmp_path: Path):
        dup = """\
tasks:
  - name: same
    prompt: "a"
    validate: "v"
  - name: same
    prompt: "b"
    validate: "v"
agents:
  - name: a1
    command: "x '{prompt}'"
"""
        f = tmp_path / "bench.yaml"
        f.write_text(dup)
        with pytest.raises(Exception, match="Duplicate task names"):
            load_config(f)

    def test_duplicate_agent_names(self, tmp_path: Path):
        dup = """\
tasks:
  - name: t1
    prompt: "a"
    validate: "v"
agents:
  - name: same
    command: "x '{prompt}'"
  - name: same
    command: "y '{prompt}'"
"""
        f = tmp_path / "bench.yaml"
        f.write_text(dup)
        with pytest.raises(Exception, match="Duplicate agent names"):
            load_config(f)

    def test_per_task_timeout_override(self, tmp_path: Path):
        f = tmp_path / "bench.yaml"
        f.write_text(VALID_YAML)
        cfg = load_config(f)

        assert cfg.tasks[0].timeout is None  # uses global
        assert cfg.tasks[1].timeout == 300   # overridden


class TestAgentConfig:
    def test_missing_prompt_placeholder(self):
        with pytest.raises(Exception, match="prompt"):
            AgentConfig(name="bad", command="agent run something")

    def test_valid_agent(self):
        a = AgentConfig(name="test", command="agent '{prompt}'")
        assert a.name == "test"


class TestParseAgentFlag:
    def test_valid_flag(self):
        a = parse_agent_flag("claude:claude --print '{prompt}'")
        assert a.name == "claude"
        assert a.command == "claude --print '{prompt}'"

    def test_no_colon(self):
        with pytest.raises(ValueError, match="Expected 'name:command'"):
            parse_agent_flag("no-colon-here")

    def test_colon_in_command(self):
        a = parse_agent_flag("agent:cmd --url http://localhost:8080 '{prompt}'")
        assert a.name == "agent"
        assert "http://localhost:8080" in a.command
