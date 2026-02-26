"""CLI entry point for agentarena.

Commands:
    agentarena run      Run the benchmark (reads bench.yaml)
    agentarena init     Create a starter bench.yaml in current directory
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from agentarena.config import BenchConfig, load_config, parse_agent_flag
from agentarena.reporter import to_json, to_csv, to_markdown
from agentarena.metrics import TaskSummary
from agentarena.runner import run_benchmark, _build_summaries

console = Console()

SAMPLE_BENCH_YAML = """\
# agentarena benchmark config
# Docs: https://github.com/manishbabel/agentarena

project: my-project
timeout: 120

tasks:
  - name: example-task
    prompt: "Fix the bug in main.py"
    validate: "python -m pytest tests/"

  # Add more tasks here:
  # - name: another-task
  #   prompt: "Add input validation to the signup form"
  #   validate: "npm test"
  #   timeout: 180    # optional per-task timeout

agents:
  - name: claude-code
    command: "claude --print '{prompt}'"
    patterns:
      tokens_in: "input tokens:\\\\s*([\\\\d,]+)"
      tokens_out: "output tokens:\\\\s*([\\\\d,]+)"
      cost: "cost:\\\\s*\\\\$?([\\\\d.]+)"

  # Add more agents here:
  # - name: aider
  #   command: "aider --message '{prompt}' --yes-always --no-git"
  #   patterns:
  #     tokens_in: "sent:\\\\s*([\\\\d,]+)"
  #     tokens_out: "received:\\\\s*([\\\\d,]+)"
  #     cost: "Cost:\\\\s*\\\\$([\\\\d.]+)"

  # No patterns = just measures time + pass/fail (works for any agent)
  # - name: my-tool
  #   command: "my-tool run '{prompt}'"
"""


@click.group()
@click.version_option()
def main():
    """agentarena — Race your AI agents. Any agent, any task, your data."""


@main.command()
@click.option(
    "--config", "-c",
    default="bench.yaml",
    type=click.Path(),
    help="Path to bench.yaml config file.",
)
@click.option(
    "--task", "-t",
    multiple=True,
    help="Run only specific task(s) by name. Can be repeated.",
)
@click.option(
    "--agent", "-a",
    multiple=True,
    help="Run only specific agent(s) by name, or add via 'name:command'. Can be repeated.",
)
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON.")
@click.option("--csv", "output_csv", is_flag=True, help="Output results as CSV.")
@click.option("--md", "output_md", is_flag=True, help="Output results as Markdown table.")
@click.option(
    "--timeout",
    type=int,
    default=None,
    help="Override global timeout (seconds).",
)
def run(
    config: str,
    task: tuple[str, ...],
    agent: tuple[str, ...],
    output_json: bool,
    output_csv: bool,
    output_md: bool,
    timeout: int | None,
):
    """Run the benchmark — race agents on your tasks."""
    config_path = Path(config)
    project_path = config_path.parent or Path.cwd()

    # Load config
    try:
        cfg = load_config(config_path)
    except FileNotFoundError:
        console.print(
            f"[red]Error:[/red] Config file not found: {config_path}\n"
            f"Run [bold]agentarena init[/bold] to create one."
        )
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Invalid config: {e}")
        raise SystemExit(1)

    # Override timeout if specified
    if timeout is not None:
        cfg = cfg.model_copy(update={"timeout": timeout})

    # Filter tasks
    if task:
        matching = [t for t in cfg.tasks if t.name in task]
        missing = set(task) - {t.name for t in matching}
        if missing:
            console.print(f"[red]Error:[/red] Unknown task(s): {', '.join(missing)}")
            console.print(f"Available: {', '.join(t.name for t in cfg.tasks)}")
            raise SystemExit(1)
        cfg = cfg.model_copy(update={"tasks": matching})

    # Filter or add agents
    if agent:
        filtered = []
        for a in agent:
            if ":" in a:
                # CLI-defined agent: "name:command {prompt}"
                try:
                    filtered.append(parse_agent_flag(a))
                except ValueError as e:
                    console.print(f"[red]Error:[/red] {e}")
                    raise SystemExit(1)
            else:
                # Filter existing agent by name
                match = [ag for ag in cfg.agents if ag.name == a]
                if not match:
                    console.print(f"[red]Error:[/red] Unknown agent: {a}")
                    console.print(f"Available: {', '.join(ag.name for ag in cfg.agents)}")
                    raise SystemExit(1)
                filtered.extend(match)
        cfg = cfg.model_copy(update={"agents": filtered})

    # Run the race
    all_runs = run_benchmark(cfg, project_path)

    # Export if requested
    if output_json:
        click.echo(to_json(all_runs))
    if output_csv:
        click.echo(to_csv(all_runs))
    if output_md:
        agents_list = [_build_agent_stub(ac) for ac in cfg.agents]
        summaries = _build_summaries(all_runs, agents_list)
        click.echo(to_markdown(summaries))


def _build_agent_stub(agent_config):
    """Lightweight agent object just for summary grouping."""
    from agentarena.agents.base import Agent
    return Agent(
        name=agent_config.name,
        command_template=agent_config.command,
        patterns=agent_config.patterns,
    )


@main.command()
@click.option(
    "--output", "-o",
    default="bench.yaml",
    type=click.Path(),
    help="Output path for the config file.",
)
def init(output: str):
    """Create a starter bench.yaml in your project."""
    path = Path(output)

    if path.exists():
        if not click.confirm(f"{path} already exists. Overwrite?"):
            console.print("[dim]Aborted.[/dim]")
            return

    path.write_text(SAMPLE_BENCH_YAML)
    console.print(f"[green]Created {path}[/green]")
    console.print(f"Edit it with your tasks and agents, then run: [bold]agentarena run[/bold]")


@main.command()
def history():
    """List past benchmark runs."""
    from agentarena.history import list_runs
    list_runs(Path.cwd())


if __name__ == "__main__":
    main()
