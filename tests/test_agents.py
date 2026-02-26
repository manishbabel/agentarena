"""Tests for config-driven agent runner."""

from pathlib import Path

import pytest

from agentarena.agents.base import Agent, AgentResult
from agentarena.config import MetricPatterns


# --- Running agents ---


class TestAgentRun:
    def test_run_simple_command(self, tmp_path: Path):
        agent = Agent(name="echo", command_template="echo '{prompt}'")
        result = agent.run("hello world", cwd=tmp_path)

        assert result.exit_code == 0
        assert "hello world" in result.stdout
        assert result.timed_out is False

    def test_run_failing_command(self, tmp_path: Path):
        agent = Agent(name="fail", command_template="exit 1 # {prompt}")
        result = agent.run("test", cwd=tmp_path)

        assert result.exit_code == 1

    def test_timeout(self, tmp_path: Path):
        agent = Agent(name="slow", command_template="sleep 10 # {prompt}")
        result = agent.run("test", cwd=tmp_path, timeout=1)

        assert result.timed_out is True
        assert result.exit_code == -1

    def test_no_patterns_no_metrics(self, tmp_path: Path):
        agent = Agent(name="echo", command_template="echo '{prompt}'")
        result = agent.run("test", cwd=tmp_path)

        assert result.tokens_in is None
        assert result.tokens_out is None
        assert result.cost_usd is None
        assert result.llm_calls is None

    def test_runs_in_correct_directory(self, tmp_path: Path):
        (tmp_path / "marker.txt").write_text("found-it")
        agent = Agent(name="cat", command_template="cat marker.txt # {prompt}")
        result = agent.run("test", cwd=tmp_path)

        assert result.exit_code == 0
        assert "found-it" in result.stdout


class TestBuildCommand:
    def test_prompt_substitution(self):
        agent = Agent(name="test", command_template="agent --msg '{prompt}'")
        cmd = agent.build_command("fix the bug")
        assert cmd == "agent --msg 'fix the bug'"

    def test_multiple_placeholders(self):
        agent = Agent(
            name="test",
            command_template="agent '{prompt}' --log '{prompt}'",
        )
        cmd = agent.build_command("hello")
        assert cmd == "agent 'hello' --log 'hello'"


# --- Regex pattern parsing ---


class TestPatternParsing:
    """Test that regex patterns from bench.yaml extract metrics correctly."""

    def _make_agent(self, **pattern_kwargs) -> Agent:
        return Agent(
            name="test",
            command_template="echo '{prompt}'",
            patterns=MetricPatterns(**pattern_kwargs),
        )

    def test_parses_all_metrics(self):
        agent = self._make_agent(
            tokens_in=r"input tokens:\s*([\d,]+)",
            tokens_out=r"output tokens:\s*([\d,]+)",
            cost=r"cost:\s*\$?([\d.]+)",
            llm_calls=r"(\d+)\s*LLM calls",
        )
        output = """
Fixed the type error in auth.ts.

Total input tokens: 4,200
Total output tokens: 850
Total cost: $0.08
3 LLM calls
"""
        result = agent._parse_output(output, "")
        assert result["tokens_in"] == 4200
        assert result["tokens_out"] == 850
        assert result["cost_usd"] == 0.08
        assert result["llm_calls"] == 3

    def test_parses_without_commas(self):
        agent = self._make_agent(
            tokens_in=r"input tokens:\s*([\d,]+)",
            tokens_out=r"output tokens:\s*([\d,]+)",
            cost=r"cost:\s*\$?([\d.]+)",
        )
        output = "input tokens: 3000\noutput tokens: 500\ncost: $0.12"
        result = agent._parse_output(output, "")
        assert result["tokens_in"] == 3000
        assert result["tokens_out"] == 500
        assert result["cost_usd"] == 0.12

    def test_parses_from_stderr(self):
        agent = self._make_agent(
            tokens_in=r"input tokens:\s*([\d,]+)",
            tokens_out=r"output tokens:\s*([\d,]+)",
        )
        result = agent._parse_output("", "input tokens: 100\noutput tokens: 50")
        assert result["tokens_in"] == 100
        assert result["tokens_out"] == 50

    def test_no_match_returns_empty(self):
        agent = self._make_agent(
            tokens_in=r"input tokens:\s*([\d,]+)",
        )
        result = agent._parse_output("random output with no metrics", "")
        assert result == {}

    def test_partial_match(self):
        agent = self._make_agent(
            tokens_in=r"input tokens:\s*([\d,]+)",
            cost=r"cost:\s*\$?([\d.]+)",
        )
        result = agent._parse_output("input tokens: 500\nno cost info here", "")
        assert result["tokens_in"] == 500
        assert "cost_usd" not in result

    def test_no_patterns_returns_empty(self):
        agent = Agent(name="test", command_template="echo '{prompt}'")
        result = agent._parse_output("input tokens: 500", "")
        assert result == {}

    def test_aider_style_output(self):
        """Aider has a different output format — regex handles it."""
        agent = self._make_agent(
            tokens_in=r"sent:\s*([\d,]+)",
            tokens_out=r"received:\s*([\d,]+)",
            cost=r"Cost:\s*\$?([\d.]+)",
        )
        output = "Tokens: sent: 3,200 received: 1,100\nCost: $0.05"
        result = agent._parse_output(output, "")
        assert result["tokens_in"] == 3200
        assert result["tokens_out"] == 1100
        assert result["cost_usd"] == 0.05
