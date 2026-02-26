# agentarena

> Race your AI agents. Any agent, any task, your data.

[![CI](https://github.com/manishbabel/agentarena/actions/workflows/ci.yml/badge.svg)](https://github.com/manishbabel/agentarena/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/agentarena.svg)](https://pypi.org/project/agentarena/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

```
$ agentarena run

 agentarena v0.1.0 — racing 3 agents on 3 tasks
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

## Why agentarena?

Every company building AI is asking the same question: **which agent actually works best?**

Today that answer is opinions, blog posts, and vibes. Your manager asks for a POC — you spend two weeks manually testing three tools and write a Google Doc that says "I think Claude was better."

**agentarena gives you hard numbers in 30 minutes:**

| Who you are | What you get |
|---|---|
| **Developer picking a tool** | Run agents on YOUR codebase, see which passes more tests, costs less, runs faster |
| **Team doing a POC** | One command, one report — give your manager data, not opinions |
| **Agent builder** | Prove your agent beats competitors with reproducible benchmarks |
| **Company evaluating vendors** | Compare digital workers on your actual workload |

Inspired by the [ActionEngine paper](https://arxiv.org/abs/2602.20502) which found **11.8x cost differences** and **5.67x token usage variance** between agent architectures on identical tasks. agentarena makes these differences visible on your own data.

## Install

```bash
pip install agentarena
```

## Quick Start

**1. Create a `bench.yaml` in your project:**

```bash
agentarena init
```

**2. Define your tasks and agents:**

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
    patterns:                                          # optional: extract metrics
      tokens_in: "input tokens:\\s*([\\d,]+)"
      tokens_out: "output tokens:\\s*([\\d,]+)"
      cost: "cost:\\s*\\$?([\\d.]+)"

  - name: aider
    command: "aider --message '{prompt}' --yes-always --no-git"

  - name: my-custom-agent                              # any CLI tool works
    command: "my-tool run '{prompt}'"
```

**3. Run the race:**

```bash
agentarena run
```

## How It Works

For each **task** x **agent** combination:

1. Creates a clean **sandbox** (git worktree for code repos, temp directory for anything else)
2. Runs the agent CLI with your prompt
3. Runs your **validation command** (tests, typecheck, lint — anything with an exit code)
4. Collects **metrics**: wall time, tokens, cost, LLM calls, pass/fail
5. Cleans up the sandbox

Works with **any project** — git repos, plain directories, any language, any domain.

## CLI

```bash
agentarena run                          # Race all agents on all tasks
agentarena run --task fix-type-error    # Run specific task
agentarena run --agent claude-code      # Run specific agent
agentarena run --json                   # Export as JSON
agentarena run --csv                    # Export as CSV
agentarena run --md                     # Export as Markdown
agentarena init                         # Create starter bench.yaml
agentarena history                      # List past runs
```

## Metric Extraction

agentarena uses **regex patterns** defined in your config to extract metrics from agent output. No code changes needed for new agents:

```yaml
agents:
  - name: my-agent
    command: "my-agent '{prompt}'"
    patterns:
      tokens_in: "Input:\\s*(\\d+) tokens"        # regex with one capture group
      tokens_out: "Output:\\s*(\\d+) tokens"
      cost: "Total:\\s*\\$([\\d.]+)"
      llm_calls: "(\\d+) API calls"
```

No patterns? agentarena still measures **wall time** and **pass/fail** — works for any tool.

## Examples

See [`examples/`](examples/) for ready-to-use configs:

- [`python-pytest.yaml`](examples/python-pytest.yaml) — Python with pytest, mypy, bandit
- [`node-typescript.yaml`](examples/node-typescript.yaml) — TypeScript with tsc, jest, ESLint
- [`react-nextjs.yaml`](examples/react-nextjs.yaml) — Next.js with vitest
- [`go.yaml`](examples/go.yaml) — Go with go test, race detector

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

[MIT](LICENSE)
