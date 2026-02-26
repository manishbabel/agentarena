"""Core benchmark runner — the race organizer.

For each task × agent combination:
  1. Create sandbox (git worktree or temp dir)
  2. Run the agent with the task prompt
  3. Run the validation command
  4. Record metrics (time, pass/fail, tokens, cost)
  5. Clean up sandbox

Hands all results to the reporter for display.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from agentarena.agents.base import Agent
from agentarena.config import AgentConfig, BenchConfig, TaskConfig
from agentarena.history import save_run
from agentarena.metrics import RunMetrics, TaskSummary, Timer
from agentarena.reporter import print_header, print_task_result, print_summary
from agentarena.sandbox import create_sandbox, cleanup_sandbox
from agentarena.validator import run_validation


console = Console()


def _build_agent(agent_config: AgentConfig) -> Agent:
    """Create an Agent from config."""
    return Agent(
        name=agent_config.name,
        command_template=agent_config.command,
        patterns=agent_config.patterns,
    )


def _run_single(
    agent: Agent,
    task: TaskConfig,
    project_path: Path,
    global_timeout: int,
    base_ref: str,
) -> RunMetrics:
    """Run one agent on one task. Returns metrics for that run."""
    timeout = task.timeout or global_timeout
    metrics = RunMetrics(agent_name=agent.name, task_name=task.name)

    # 1. Create sandbox
    try:
        sandbox_path = create_sandbox(project_path, ref=base_ref)
    except RuntimeError as e:
        metrics.error = f"Sandbox creation failed: {e}"
        console.print(f"    [red]ERROR[/red] sandbox failed: {e}")
        return metrics

    try:
        # 2. Run agent
        with Timer() as t:
            agent_result = agent.run(prompt=task.prompt, cwd=sandbox_path, timeout=timeout)

        metrics.wall_time_seconds = t.elapsed
        metrics.tokens_in = agent_result.tokens_in
        metrics.tokens_out = agent_result.tokens_out
        metrics.cost_usd = agent_result.cost_usd
        metrics.llm_calls = agent_result.llm_calls
        metrics.timed_out = agent_result.timed_out

        if agent_result.timed_out:
            metrics.passed = False
            return metrics

        # 3. Validate
        validation = run_validation(
            command=task.validate_command,
            cwd=sandbox_path,
            timeout=timeout,
        )
        metrics.passed = validation.passed

        if validation.timed_out:
            metrics.timed_out = True

    except Exception as e:
        metrics.error = str(e)
        console.print(f"    [red]ERROR[/red] {e}")

    finally:
        # 4. Cleanup
        cleanup_sandbox(project_path, sandbox_path)

    return metrics


def run_benchmark(config: BenchConfig, project_path: Path) -> list[RunMetrics]:
    """Run the full benchmark — all tasks × all agents.

    Args:
        config: Parsed bench.yaml config.
        project_path: Root of the project to benchmark.

    Returns:
        List of RunMetrics, one per (task, agent) pair.
    """
    agents = [_build_agent(ac) for ac in config.agents]
    all_runs: list[RunMetrics] = []

    # Header
    print_header(
        project=config.project,
        num_agents=len(agents),
        num_tasks=len(config.tasks),
    )

    # Run each task × agent
    for task_idx, task in enumerate(config.tasks, start=1):
        task_runs: list[RunMetrics] = []

        for agent in agents:
            console.print(f"  [dim]Running {agent.name} on {task.name}...[/dim]")

            metrics = _run_single(
                agent=agent,
                task=task,
                project_path=project_path,
                global_timeout=config.timeout,
                base_ref=config.base,
            )
            task_runs.append(metrics)
            all_runs.append(metrics)

        # Print per-task results
        print_task_result(
            task_name=task.name,
            task_prompt=task.prompt,
            task_index=task_idx,
            total_tasks=len(config.tasks),
            runs=task_runs,
        )

    # Build summaries (one per agent)
    summaries = _build_summaries(all_runs, agents)
    print_summary(summaries)

    # Save run history
    saved = save_run(project_path, config.project, all_runs, summaries)
    console.print(f"\n  [dim]Results saved to {saved}[/dim]")

    return all_runs


def _build_summaries(all_runs: list[RunMetrics], agents: list[Agent]) -> list[TaskSummary]:
    """Group runs by agent and build summary stats."""
    summaries = []
    for agent in agents:
        agent_runs = [r for r in all_runs if r.agent_name == agent.name]
        summaries.append(TaskSummary(agent_name=agent.name, runs=agent_runs))
    return summaries
