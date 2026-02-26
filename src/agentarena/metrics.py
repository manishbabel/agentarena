"""Metrics collection — time, tokens, cost, LLM calls.

RunMetrics is the core data structure: one instance per (agent, task) pair.
It holds everything we measure — wall time, pass/fail, and optional
token/cost data that agent adapters can fill in.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RunMetrics:
    """Metrics for a single agent run on a single task."""

    agent_name: str
    task_name: str
    passed: bool = False
    wall_time_seconds: float = 0.0
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    llm_calls: int | None = None
    timed_out: bool = False
    error: str | None = None

    @property
    def total_tokens(self) -> int | None:
        """Total tokens (input + output), or None if not available."""
        if self.tokens_in is not None and self.tokens_out is not None:
            return self.tokens_in + self.tokens_out
        return None


@dataclass
class TaskSummary:
    """Aggregated results for one agent across all tasks."""

    agent_name: str
    runs: list[RunMetrics] = field(default_factory=list)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.runs if r.passed)

    @property
    def total_count(self) -> int:
        return len(self.runs)

    @property
    def pass_rate(self) -> float:
        return self.pass_count / self.total_count if self.total_count > 0 else 0.0

    @property
    def avg_time(self) -> float:
        if not self.runs:
            return 0.0
        return sum(r.wall_time_seconds for r in self.runs) / len(self.runs)

    @property
    def avg_cost(self) -> float | None:
        costs = [r.cost_usd for r in self.runs if r.cost_usd is not None]
        if not costs:
            return None
        return sum(costs) / len(costs)

    @property
    def total_tokens_sum(self) -> int | None:
        totals = [r.total_tokens for r in self.runs if r.total_tokens is not None]
        if not totals:
            return None
        return sum(totals)


class Timer:
    """Context manager to measure wall-clock time.

    Usage:
        with Timer() as t:
            do_something()
        print(t.elapsed)  # seconds as float
    """

    def __init__(self) -> None:
        self.elapsed: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> Timer:
        self._start = time.monotonic()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed = round(time.monotonic() - self._start, 2)
