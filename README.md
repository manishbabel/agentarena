# agentrace

> Race your AI agents. Any agent, any task, your data.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

agentrace lets you benchmark and compare AI agents — coding agents, domain agents, digital workers — by running them on **your** tasks with **your** data. Measure what matters: pass/fail, time, cost, token usage, and LLM call counts.

```
$ agentrace run

 agentrace v0.1.0 — racing 3 agents on 3 tasks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Task 1/3: fix-type-error
   claude-code ····· PASS   15s   $0.08   4.2K tokens   2 calls
   aider ··········· PASS   23s   $0.14   8.7K tokens   5 calls
   codex ··········· PASS   31s   $0.21  12.1K tokens   8 calls

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

              Pass Rate   Avg Time   Avg Cost   Total Tokens
 claude-code  3/3 100%      45s       $0.20       34.6K
 aider        2/3  67%      69s       $0.35       65.2K
 codex        2/3  67%      71s       $0.42       82.2K

 Winner: claude-code (highest pass rate, lowest cost)
```

## Use Cases

- **Pick the right tool** — Which AI coding agent works best on YOUR codebase?
- **POC evaluations** — Give your manager hard numbers, not opinions
- **Compare digital workers** — Any agent with a CLI or API, not just coding tools
- **Prove your agent wins** — Agent builders: use agentrace results as proof

## Install

```bash
pip install agentrace
```

## Quick Start

**1. Create a `bench.yaml` in your project:**

```bash
agentrace init
```

**2. Define tasks and agents:**

```yaml
project: my-app
timeout: 120

tasks:
  - name: fix-type-error
    prompt: "Fix the TypeScript type error in src/auth/login.ts"
    validate: "npx tsc --noEmit"

  - name: add-pagination
    prompt: "Add offset/limit pagination to GET /api/users endpoint"
    validate: "bun test test/api/users.test.ts"

agents:
  - name: claude-code
    command: "claude --print --max-turns 10 '{prompt}'"

  - name: aider
    command: "aider --message '{prompt}' --yes-always --no-git"
```

**3. Run the race:**

```bash
agentrace run
```

## How It Works

1. For each **task** x **agent** combination:
   - Creates a clean **sandbox** (git worktree or temp directory)
   - Runs the agent CLI with your prompt
   - Runs your **validation command** (tests, typecheck, lint, scripts)
   - Collects **metrics**: wall time, tokens, cost, LLM calls, pass/fail
   - Cleans up the sandbox

2. Produces a **comparison table** showing which agent wins.

Works with **any project** — git repos, plain directories, any language, any domain.

## CLI Usage

```bash
agentrace run                          # Run all tasks x all agents
agentrace run --task fix-type-error    # Run specific task
agentrace run --agent claude-code      # Run specific agent
agentrace run --json                   # Output as JSON
agentrace run --csv                    # Output as CSV
agentrace init                         # Generate sample bench.yaml
agentrace history                      # List past runs
```

## Adding Custom Agents

Any tool with a CLI works. Just provide a command with a `{prompt}` placeholder:

```yaml
agents:
  - name: my-agent
    command: "my-tool --input '{prompt}' --auto"
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

[MIT](LICENSE)
