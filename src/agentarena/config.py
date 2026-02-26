"""Parse and validate bench.yaml configuration."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class TaskConfig(BaseModel):
    """A single benchmark task."""

    model_config = {"populate_by_name": True}

    name: str
    prompt: str
    validate_command: str = Field(alias="validate")
    timeout: int | None = None  # per-task override; falls back to global


class MetricPatterns(BaseModel):
    """Regex patterns to extract metrics from agent output.

    Each pattern should have exactly one capture group.
    Example: "input tokens:\\s*([\\d,]+)"
    """

    tokens_in: str | None = None
    tokens_out: str | None = None
    cost: str | None = None
    llm_calls: str | None = None


class AgentConfig(BaseModel):
    """A single agent to benchmark."""

    name: str
    command: str
    patterns: MetricPatterns | None = None

    @field_validator("command")
    @classmethod
    def command_must_have_prompt_placeholder(cls, v: str) -> str:
        if "{prompt}" not in v:
            raise ValueError("Agent command must contain '{prompt}' placeholder")
        return v


class BenchConfig(BaseModel):
    """Top-level bench.yaml configuration."""

    project: str = "default"
    base: str = "HEAD"
    timeout: int = Field(default=120, ge=1)
    tasks: list[TaskConfig] = Field(min_length=1)
    agents: list[AgentConfig] = Field(min_length=1)

    @field_validator("tasks")
    @classmethod
    def task_names_must_be_unique(cls, v: list[TaskConfig]) -> list[TaskConfig]:
        names = [t.name for t in v]
        dupes = [n for n in names if names.count(n) > 1]
        if dupes:
            raise ValueError(f"Duplicate task names: {set(dupes)}")
        return v

    @field_validator("agents")
    @classmethod
    def agent_names_must_be_unique(cls, v: list[AgentConfig]) -> list[AgentConfig]:
        names = [a.name for a in v]
        dupes = [n for n in names if names.count(n) > 1]
        if dupes:
            raise ValueError(f"Duplicate agent names: {set(dupes)}")
        return v


def load_config(path: Path) -> BenchConfig:
    """Load and validate a bench.yaml file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid config: expected a YAML mapping, got {type(raw).__name__}")

    return BenchConfig(**raw)


def parse_agent_flag(flag: str) -> AgentConfig:
    """Parse a CLI --agent flag like 'name:command {prompt}'.

    Format: "agent-name:shell command with {prompt}"
    """
    if ":" not in flag:
        raise ValueError(f"Invalid --agent format: '{flag}'. Expected 'name:command'")

    name, command = flag.split(":", 1)
    return AgentConfig(name=name.strip(), command=command.strip())
