"""Agent runner — runs any agent and parses output via config-driven regex.

No per-agent files needed. Users define regex patterns in bench.yaml:

    agents:
      - name: claude-code
        command: "claude --print '{prompt}'"
        patterns:
          tokens_in: "input tokens:\\s*([\\d,]+)"
          tokens_out: "output tokens:\\s*([\\d,]+)"
          cost: "cost:\\s*\\$?([\\d.]+)"

      - name: some-tool       # no patterns = just time + pass/fail
        command: "tool '{prompt}'"
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agentrace.config import MetricPatterns
from agentrace.metrics import Timer


@dataclass
class AgentResult:
    """What we get back after running an agent."""

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    llm_calls: int | None = None


class Agent:
    """Runs any agent CLI and extracts metrics using regex patterns.

    Works for every agent — Claude, Aider, Codex, or any custom tool.
    If no patterns provided, still measures wall time + pass/fail.
    """

    def __init__(
        self,
        name: str,
        command_template: str,
        patterns: MetricPatterns | None = None,
    ) -> None:
        self.name = name
        self.command_template = command_template
        self.patterns = patterns

    def build_command(self, prompt: str) -> str:
        """Substitute {prompt} into the command template."""
        return self.command_template.replace("{prompt}", prompt)

    def run(self, prompt: str, cwd: Path, timeout: int = 120) -> AgentResult:
        """Run the agent and return structured results."""
        command = self.build_command(prompt)

        try:
            with Timer() as t:
                proc = subprocess.run(
                    command,
                    shell=True,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

            result = AgentResult(
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
            )

        except subprocess.TimeoutExpired:
            return AgentResult(
                stdout="",
                stderr=f"Agent timed out after {timeout}s",
                exit_code=-1,
                timed_out=True,
            )

        # Parse metrics from output using regex patterns
        if self.patterns:
            parsed = self._parse_output(result.stdout, result.stderr)
            result.tokens_in = parsed.get("tokens_in")
            result.tokens_out = parsed.get("tokens_out")
            result.cost_usd = parsed.get("cost_usd")
            result.llm_calls = parsed.get("llm_calls")

        return result

    def _parse_output(self, stdout: str, stderr: str) -> dict:
        """Extract metrics using regex patterns from config."""
        combined = stdout + "\n" + stderr
        result: dict = {}

        if not self.patterns:
            return result

        # tokens_in: extract int (handles commas like "4,200")
        if self.patterns.tokens_in:
            m = re.search(self.patterns.tokens_in, combined, re.IGNORECASE)
            if m:
                result["tokens_in"] = int(m.group(1).replace(",", ""))

        # tokens_out: same
        if self.patterns.tokens_out:
            m = re.search(self.patterns.tokens_out, combined, re.IGNORECASE)
            if m:
                result["tokens_out"] = int(m.group(1).replace(",", ""))

        # cost: extract float
        if self.patterns.cost:
            m = re.search(self.patterns.cost, combined, re.IGNORECASE)
            if m:
                result["cost_usd"] = float(m.group(1))

        # llm_calls: extract int
        if self.patterns.llm_calls:
            m = re.search(self.patterns.llm_calls, combined, re.IGNORECASE)
            if m:
                result["llm_calls"] = int(m.group(1).replace(",", ""))

        return result
