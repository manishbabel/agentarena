"""Tests for metrics collection."""

import time

from agentrace.metrics import RunMetrics, TaskSummary, Timer


class TestRunMetrics:
    def test_total_tokens_both_set(self):
        m = RunMetrics(agent_name="a", task_name="t", tokens_in=100, tokens_out=50)
        assert m.total_tokens == 150

    def test_total_tokens_none_if_missing(self):
        m = RunMetrics(agent_name="a", task_name="t", tokens_in=100)
        assert m.total_tokens is None

    def test_total_tokens_none_if_both_missing(self):
        m = RunMetrics(agent_name="a", task_name="t")
        assert m.total_tokens is None

    def test_defaults(self):
        m = RunMetrics(agent_name="a", task_name="t")
        assert m.passed is False
        assert m.wall_time_seconds == 0.0
        assert m.cost_usd is None
        assert m.llm_calls is None
        assert m.timed_out is False
        assert m.error is None


class TestTaskSummary:
    def test_pass_rate(self):
        s = TaskSummary(
            agent_name="a",
            runs=[
                RunMetrics(agent_name="a", task_name="t1", passed=True),
                RunMetrics(agent_name="a", task_name="t2", passed=False),
                RunMetrics(agent_name="a", task_name="t3", passed=True),
            ],
        )
        assert s.pass_count == 2
        assert s.total_count == 3
        assert abs(s.pass_rate - 2 / 3) < 0.01

    def test_empty_runs(self):
        s = TaskSummary(agent_name="a")
        assert s.pass_rate == 0.0
        assert s.avg_time == 0.0
        assert s.avg_cost is None
        assert s.total_tokens_sum is None

    def test_avg_time(self):
        s = TaskSummary(
            agent_name="a",
            runs=[
                RunMetrics(agent_name="a", task_name="t1", wall_time_seconds=10.0),
                RunMetrics(agent_name="a", task_name="t2", wall_time_seconds=20.0),
            ],
        )
        assert s.avg_time == 15.0

    def test_avg_cost_skips_none(self):
        s = TaskSummary(
            agent_name="a",
            runs=[
                RunMetrics(agent_name="a", task_name="t1", cost_usd=0.10),
                RunMetrics(agent_name="a", task_name="t2"),  # no cost
                RunMetrics(agent_name="a", task_name="t3", cost_usd=0.30),
            ],
        )
        assert s.avg_cost == 0.20

    def test_total_tokens_sum(self):
        s = TaskSummary(
            agent_name="a",
            runs=[
                RunMetrics(agent_name="a", task_name="t1", tokens_in=100, tokens_out=50),
                RunMetrics(agent_name="a", task_name="t2", tokens_in=200, tokens_out=100),
            ],
        )
        assert s.total_tokens_sum == 450


class TestTimer:
    def test_measures_time(self):
        with Timer() as t:
            time.sleep(0.1)
        assert t.elapsed >= 0.1
        assert t.elapsed < 0.5  # generous upper bound

    def test_zero_when_instant(self):
        with Timer() as t:
            pass
        assert t.elapsed >= 0.0
        assert t.elapsed < 0.1
