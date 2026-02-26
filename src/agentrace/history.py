"""Run history — save and list past benchmark results.

Each run is saved as a JSON file in .agentrace/runs/.
Users can compare how agents perform over time.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from agentrace.metrics import RunMetrics, TaskSummary

HISTORY_DIR = ".agentrace/runs"

console = Console()


def save_run(
    project_path: Path,
    config_project: str,
    all_runs: list[RunMetrics],
    summaries: list[TaskSummary],
) -> Path:
    """Save a benchmark run to .agentrace/runs/<timestamp>.json.

    Returns the path to the saved file.
    """
    history_dir = project_path / HISTORY_DIR
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}.json"
    filepath = history_dir / filename

    # Find winner
    winner = None
    if summaries:
        best = sorted(summaries, key=lambda s: (-s.pass_rate, s.avg_cost or float("inf")))[0]
        winner = best.agent_name

    data = {
        "timestamp": timestamp,
        "project": config_project,
        "num_tasks": len({r.task_name for r in all_runs}),
        "num_agents": len({r.agent_name for r in all_runs}),
        "winner": winner,
        "summary": [
            {
                "agent": s.agent_name,
                "pass_count": s.pass_count,
                "total_count": s.total_count,
                "pass_rate": round(s.pass_rate, 2),
                "avg_time": round(s.avg_time, 2),
                "avg_cost": round(s.avg_cost, 2) if s.avg_cost is not None else None,
                "total_tokens": s.total_tokens_sum,
            }
            for s in summaries
        ],
        "runs": [asdict(r) for r in all_runs],
    }

    filepath.write_text(json.dumps(data, indent=2))
    return filepath


def list_runs(project_path: Path) -> None:
    """Print a table of past benchmark runs."""
    history_dir = project_path / HISTORY_DIR

    if not history_dir.exists():
        console.print("[dim]No runs yet. Run [bold]agentrace run[/bold] first.[/dim]")
        return

    files = sorted(history_dir.glob("*.json"), reverse=True)

    if not files:
        console.print("[dim]No runs yet. Run [bold]agentrace run[/bold] first.[/dim]")
        return

    table = Table(show_header=True, title="Past Runs")
    table.add_column("#", style="dim", min_width=4)
    table.add_column("Date", min_width=20)
    table.add_column("Tasks", justify="center", min_width=6)
    table.add_column("Agents", justify="center", min_width=7)
    table.add_column("Winner", style="green bold", min_width=15)
    table.add_column("File", style="dim", min_width=20)

    for i, f in enumerate(files, start=1):
        try:
            data = json.loads(f.read_text())
            table.add_row(
                str(i),
                data.get("timestamp", "?"),
                str(data.get("num_tasks", "?")),
                str(data.get("num_agents", "?")),
                data.get("winner", "-"),
                f.name,
            )
        except (json.JSONDecodeError, KeyError):
            table.add_row(str(i), "?", "?", "?", "?", f.name)

    console.print(table)
