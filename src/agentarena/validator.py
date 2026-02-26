"""Run user-defined validation commands and check results.

After an agent modifies code in a worktree, the validator runs the user's
check command (e.g. "pytest", "tsc --noEmit") and reports pass/fail based
on exit code.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of running a validation command."""

    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


def run_validation(
    command: str,
    cwd: Path,
    timeout: int = 120,
) -> ValidationResult:
    """Run a validation command and return the result.

    Args:
        command: Shell command to execute (e.g. "pytest tests/").
        cwd: Working directory to run in (the worktree path).
        timeout: Max seconds before killing the process.

    Returns:
        ValidationResult with pass/fail, output, and timing.
    """
    start = time.monotonic()

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.monotonic() - start

        return ValidationResult(
            passed=proc.returncode == 0,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_seconds=round(duration, 2),
        )

    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        return ValidationResult(
            passed=False,
            exit_code=-1,
            stdout="",
            stderr=f"Validation timed out after {timeout}s",
            duration_seconds=round(duration, 2),
            timed_out=True,
        )
