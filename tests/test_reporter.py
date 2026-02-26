"""Tests for the terminal reporter and export formats."""

import json

from agentrace.metrics import RunMetrics, TaskSummary
from agentrace.reporter import (
    _format_time,
    _format_tokens,
    _format_cost,
    _pick_winner,
    to_json,
    to_csv,
    to_markdown,
)


# --- Formatting helpers ---


class TestFormatTime:
    def test_seconds(self):
        assert _format_time(45) == "45s"

    def test_minutes(self):
        assert _format_time(125) == "2m5s"

    def test_zero(self):
        assert _format_time(0) == "0s"


class TestFormatTokens:
    def test_thousands(self):
        assert _format_tokens(4200) == "4.2K"

    def test_small(self):
        assert _format_tokens(500) == "500"

    def test_none(self):
        assert _format_tokens(None) == "-"


class TestFormatCost:
    def test_normal(self):
        assert _format_cost(0.08) == "$0.08"

    def test_none(self):
        assert _format_cost(None) == "-"

    def test_over_dollar(self):
        assert _format_cost(1.5) == "$1.50"


# --- Winner selection ---


class TestPickWinner:
    def _summary(self, name: str, passed: int, total: int, avg_cost: float = 0.1) -> TaskSummary:
        runs = []
        for i in range(total):
            runs.append(RunMetrics(
                agent_name=name,
                task_name=f"t{i}",
                passed=i < passed,
                wall_time_seconds=10.0,
                cost_usd=avg_cost,
            ))
        return TaskSummary(agent_name=name, runs=runs)

    def test_highest_pass_rate_wins(self):
        a = self._summary("a", passed=3, total=3)
        b = self._summary("b", passed=2, total=3)
        assert _pick_winner([a, b]).agent_name == "a"

    def test_tie_on_pass_rate_lowest_cost_wins(self):
        a = self._summary("a", passed=3, total=3, avg_cost=0.50)
        b = self._summary("b", passed=3, total=3, avg_cost=0.20)
        assert _pick_winner([a, b]).agent_name == "b"

    def test_empty_returns_none(self):
        assert _pick_winner([]) is None


# --- Export: JSON ---


class TestToJson:
    def test_valid_json(self):
        runs = [
            RunMetrics(agent_name="a", task_name="t1", passed=True, wall_time_seconds=10.0),
        ]
        result = json.loads(to_json(runs))
        assert len(result) == 1
        assert result[0]["agent_name"] == "a"
        assert result[0]["passed"] is True

    def test_empty(self):
        result = json.loads(to_json([]))
        assert result == []


# --- Export: CSV ---


class TestToCsv:
    def test_has_headers_and_data(self):
        runs = [
            RunMetrics(agent_name="a", task_name="t1", passed=True, wall_time_seconds=10.0),
            RunMetrics(agent_name="b", task_name="t1", passed=False, wall_time_seconds=20.0),
        ]
        result = to_csv(runs)
        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
        assert "agent_name" in lines[0]
        assert "a" in lines[1]
        assert "b" in lines[2]

    def test_empty(self):
        assert to_csv([]) == ""


# --- Export: Markdown ---


class TestToMarkdown:
    def test_table_format(self):
        s = TaskSummary(
            agent_name="claude",
            runs=[
                RunMetrics(agent_name="claude", task_name="t1", passed=True,
                           wall_time_seconds=45, tokens_in=3000, tokens_out=1200, cost_usd=0.20),
            ],
        )
        result = to_markdown([s])
        assert "| claude" in result
        assert "1/1 100%" in result
        assert "$0.20" in result
        assert "4.2K" in result  # 3000 + 1200

    def test_multiple_agents(self):
        summaries = [
            TaskSummary(agent_name="a", runs=[
                RunMetrics(agent_name="a", task_name="t1", passed=True, wall_time_seconds=10),
            ]),
            TaskSummary(agent_name="b", runs=[
                RunMetrics(agent_name="b", task_name="t1", passed=False, wall_time_seconds=20),
            ]),
        ]
        result = to_markdown(summaries)
        assert "| a " in result
        assert "| b " in result
