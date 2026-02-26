"""Rich terminal output — the scoreboard people screenshot and share.

Two main outputs:
  1. Per-task results: each task shows how every agent did
  2. Summary table:    aggregated stats + winner declaration

Also supports JSON, CSV, and Markdown export.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentarena.metrics import RunMetrics, TaskSummary


console = Console()


def _format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m{secs}s"


def _format_tokens(count: int | None) -> str:
    if count is None:
        return "-"
    if count >= 1000:
        return f"{count / 1000:.1f}K"
    return str(count)


def _format_cost(cost: float | None) -> str:
    if cost is None:
        return "-"
    return f"${cost:.2f}"


def _pass_text(passed: bool, timed_out: bool = False) -> Text:
    if timed_out:
        return Text("TIMEOUT", style="yellow bold")
    if passed:
        return Text("PASS", style="green bold")
    return Text("FAIL", style="red bold")


# --- Per-task results ---


def print_task_result(
    task_name: str,
    task_prompt: str,
    task_index: int,
    total_tasks: int,
    runs: list[RunMetrics],
) -> None:
    """Print results for a single task — one row per agent."""
    console.print()
    console.rule(f"[bold]Task {task_index}/{total_tasks}: {task_name}[/bold]")
    console.print(f"  [dim]{task_prompt}[/dim]")
    console.print()

    table = Table(show_header=True, show_edge=False, pad_edge=False, box=None)
    table.add_column("Agent", style="cyan", min_width=15)
    table.add_column("Result", justify="center", min_width=8)
    table.add_column("Time", justify="right", min_width=8)
    table.add_column("Cost", justify="right", min_width=8)
    table.add_column("Tokens", justify="right", min_width=10)
    table.add_column("LLM Calls", justify="right", min_width=10)

    for run in runs:
        table.add_row(
            run.agent_name,
            _pass_text(run.passed, run.timed_out),
            _format_time(run.wall_time_seconds),
            _format_cost(run.cost_usd),
            _format_tokens(run.total_tokens),
            str(run.llm_calls) if run.llm_calls is not None else "-",
        )

    console.print(table)


# --- Summary table ---


def print_summary(summaries: list[TaskSummary]) -> None:
    """Print the final scoreboard — aggregated stats per agent + winner."""
    console.print()
    console.rule("[bold]RESULTS[/bold]")
    console.print()

    table = Table(show_header=True, show_edge=False, box=None)
    table.add_column("Agent", style="cyan bold", min_width=15)
    table.add_column("Pass Rate", justify="center", min_width=12)
    table.add_column("Avg Time", justify="right", min_width=10)
    table.add_column("Avg Cost", justify="right", min_width=10)
    table.add_column("Total Tokens", justify="right", min_width=13)

    for s in summaries:
        pass_str = f"{s.pass_count}/{s.total_count} {s.pass_rate:.0%}"
        table.add_row(
            s.agent_name,
            pass_str,
            _format_time(s.avg_time),
            _format_cost(s.avg_cost),
            _format_tokens(s.total_tokens_sum),
        )

    console.print(table)

    # Declare winner
    winner = _pick_winner(summaries)
    if winner:
        console.print()
        console.print(
            Panel(
                f"[bold green]{winner.agent_name}[/bold green] wins "
                f"({winner.pass_count}/{winner.total_count} passed, "
                f"{_format_cost(winner.avg_cost)} avg cost)",
                title="[bold]Winner[/bold]",
                border_style="green",
            )
        )


def _pick_winner(summaries: list[TaskSummary]) -> TaskSummary | None:
    """Pick the winner: highest pass rate, then lowest avg cost, then fastest."""
    if not summaries:
        return None

    return sorted(
        summaries,
        key=lambda s: (
            -s.pass_rate,           # highest pass rate first
            s.avg_cost or float("inf"),  # lowest cost
            s.avg_time,             # fastest
        ),
    )[0]


# --- Header ---


def print_header(project: str, num_agents: int, num_tasks: int) -> None:
    """Print the agentarena banner at the start of a run."""
    console.print()
    console.print(
        Panel(
            f"[bold]agentarena[/bold] v0.1.0 — racing "
            f"[cyan]{num_agents}[/cyan] agents on "
            f"[cyan]{num_tasks}[/cyan] tasks\n"
            f"project: [dim]{project}[/dim]",
            border_style="blue",
        )
    )


# --- Export formats ---


def to_json(all_runs: list[RunMetrics]) -> str:
    """Export all run results as JSON."""
    data = [asdict(r) for r in all_runs]
    return json.dumps(data, indent=2)


def to_csv(all_runs: list[RunMetrics]) -> str:
    """Export all run results as CSV."""
    if not all_runs:
        return ""

    output = io.StringIO()
    fields = [
        "agent_name", "task_name", "passed", "wall_time_seconds",
        "tokens_in", "tokens_out", "cost_usd", "llm_calls", "timed_out",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()

    for run in all_runs:
        row = asdict(run)
        writer.writerow({k: row[k] for k in fields})

    return output.getvalue()


def to_markdown(summaries: list[TaskSummary]) -> str:
    """Export summary table as Markdown."""
    lines = [
        "| Agent | Pass Rate | Avg Time | Avg Cost | Total Tokens |",
        "|-------|-----------|----------|----------|--------------|",
    ]
    for s in summaries:
        lines.append(
            f"| {s.agent_name} "
            f"| {s.pass_count}/{s.total_count} {s.pass_rate:.0%} "
            f"| {_format_time(s.avg_time)} "
            f"| {_format_cost(s.avg_cost)} "
            f"| {_format_tokens(s.total_tokens_sum)} |"
        )
    return "\n".join(lines)
