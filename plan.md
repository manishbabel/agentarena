# agentmark — Benchmark AI Coding Agents on Your Codebase

## Objective

Build an open-source Python CLI that lets developers benchmark and compare
AI coding agents (Claude Code, Aider, Codex, etc.) on their own codebase
with their own tasks. Produce a beautiful terminal report showing
pass/fail, time, cost, token usage, and LLM call counts.

**Goal:** Become the de facto standard for answering "which AI agent works
best for MY code?" — the Hyperfine of AI coding agents.

**Viral thesis:** Benchmark comparison results are inherently shareable.
Developers will screenshot the results table and post it on Twitter/HN/Reddit.
Tribal loyalty (Claude fans vs GPT fans) drives organic engagement. Every
comparison post creates more users.

---

## Research Foundation

Based on: **"ActionEngine: From Reactive to Programmatic GUI Agents via
State Machine Memory"** — Zhong et al., 2025
(https://arxiv.org/abs/2602.20502)

### Key Paper Findings That Motivate This Tool

1. **Reactive vs programmatic agents differ by 11.8x in cost.** Reactive
   agents (observe → LLM call → act → repeat) require O(N) LLM calls.
   Programmatic agents (plan once → execute) require O(1). The paper
   measured 11.8x cost difference and 2x latency improvement for the
   same tasks. Different coding agents have different strategies —
   agentmark quantifies which are wasteful.

2. **Token usage varies 5.67x across approaches.** For identical tasks,
   input tokens ranged from 8.1K to 62.3K depending on the agent
   architecture. This is invisible without measurement.

3. **LLM calls vary 5.67x.** Average 1.8 calls (programmatic) vs 10.2
   calls (reactive) per task. Some coding agents re-read the same file
   repeatedly. agentmark exposes this.

4. **Model choice causes 20-30% failure rate differences.** With weaker
   planning models (GPT-4o), 20-30% of executions need validation and
   hot-patching. Stronger models (Claude Sonnet) rarely do. agentmark
   measures pass rates per agent.

5. **Task ambiguity causes 6% of failures.** The paper found that 6 of
   106 task failures came from ambiguous specs, not agent limitations.
   agentmark's structured task format (prompt + validation command)
   eliminates this variable.

### Paper Concept → agentmark Mapping

| Paper Concept | agentmark Feature |
|---|---|
| O(N) vs O(1) LLM calls | Measure LLM call count per agent per task |
| 11.8x cost difference | Track cost per agent per task |
| Task disambiguation | Structured bench.yaml with clear prompts + validation |
| Validator with hot-patching | Validation commands (test, typecheck, lint) |
| State machine isolation | Git worktree per run = clean reproducible state |

---

## Competitive Landscape (as of Feb 2025)

### What Exists (NOT competitors — they solve different problems)

| Tool | What It Does | Why It's Different |
|---|---|---|
| SWE-bench | Fixed GitHub issues from fixed repos | Academic; not YOUR codebase, not YOUR tasks |
| THUDM/AgentBench | Evaluates LLMs in 8 generic environments | Academic framework; not coding-focused, not personal |
| jadbox/codeagentbench | Predefined coding test cases | Fixed test cases, not your repo; 4 stars, dormant |
| Terminal-Bench | Tests AI in terminal environments | Academic; general terminal tasks, not code changes |
| Codex Arena Mode | Compare 2 models side-by-side | Built into Codex only; not cross-tool |
| Aider leaderboard | Aider + different LLMs | One tool, different models — not different agents |
| Blog comparisons | Manual side-by-side reviews | Not a tool; not reproducible; opinion-based |

### The Gap We Fill

No tool exists where you:
1. Define YOUR tasks on YOUR codebase
2. Run DIFFERENT agent CLIs (not just different models)
3. Get isolated runs (git worktrees)
4. Get structured cost/time/token/success comparison
5. Get a shareable report

---

## Architecture

### Core Loop (simple)

```
for each task in bench.yaml:
    for each agent in config:
        1. Create git worktree (clean isolated copy)
        2. Start timer + metrics collection
        3. Run agent CLI with task prompt (subprocess)
        4. Parse agent stdout/stderr for token/cost data
        5. Run validation command (test, typecheck, lint)
        6. Record: pass/fail, wall time, tokens, cost, LLM calls
        7. Remove git worktree (cleanup)

Produce comparison table + optional JSON/CSV export
```

### Project Structure

```
agentmark/
├── pyproject.toml              # Project config, dependencies, entry point
├── README.md                   # Hero demo GIF + quick start
├── src/
│   └── agentmark/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point (click or typer)
│       ├── config.py           # Parse bench.yaml
│       ├── sandbox.py          # Git worktree create/cleanup
│       ├── runner.py           # Core benchmark loop
│       ├── agents/             # Agent adapters (one per tool)
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract agent interface
│       │   ├── claude_code.py  # claude --print adapter
│       │   ├── aider.py        # aider --message adapter
│       │   └── codex.py        # codex adapter
│       ├── metrics.py          # Token/cost/time collection + parsing
│       ├── validator.py        # Run validation commands, check exit codes
│       └── reporter.py         # Rich terminal output (tables, summary)
├── tests/
│   ├── test_config.py
│   ├── test_sandbox.py
│   ├── test_runner.py
│   └── test_metrics.py
└── examples/
    └── bench.yaml              # Example task file
```

### Key Design Decisions

1. **Agents are black boxes.** We only interact via their CLI. No SDK
   integration. This keeps the tool agent-agnostic and easy to extend.
   Users add new agents by specifying a shell command.

2. **Git worktrees for isolation.** Each run gets a clean copy of the
   repo at the current commit. No cross-contamination between agents
   or tasks. Cheap to create, automatic cleanup.

3. **Validation is user-defined.** The user provides a shell command
   (e.g., `bun test`, `pytest`, `tsc --noEmit`). Pass = exit code 0.
   This keeps agentmark domain-agnostic.

4. **Metrics from stdout parsing.** Each agent adapter knows how to
   extract token counts, cost, and LLM calls from that agent's output.
   Fallback: just measure wall time and pass/fail.

5. **No LLM calls in agentmark itself.** The tool is pure orchestration
   and measurement. Zero AI cost to run the benchmarker.

---

## Task Definition Format

`bench.yaml` — lives in user's repo root:

```yaml
# Optional metadata
project: my-app
base: HEAD           # Git ref to benchmark against (default: HEAD)
timeout: 120         # Default timeout per task in seconds

# Tasks to benchmark
tasks:
  - name: fix-type-error
    prompt: "Fix the TypeScript type error in src/auth/login.ts"
    validate: "npx tsc --noEmit"

  - name: add-pagination
    prompt: "Add offset/limit pagination to GET /api/users endpoint"
    validate: "bun test test/api/users.test.ts"
    timeout: 180

  - name: write-tests
    prompt: "Write unit tests for src/payments/charge.ts achieving >80% coverage"
    validate: "bun test test/payments/"

# Agents to compare
agents:
  - name: claude-code
    command: "claude --print --max-turns 10 '{prompt}'"

  - name: aider
    command: "aider --message '{prompt}' --yes-always --no-git"

  - name: codex
    command: "codex --quiet '{prompt}'"
```

Users can also pass agents via CLI flags:
```bash
agentmark run --agent "claude-code:claude --print '{prompt}'"
agentmark run --agent "aider:aider --message '{prompt}' --yes-always"
```

---

## CLI Interface

```bash
# Initialize a bench.yaml in current repo
agentmark init

# Run all tasks against all agents
agentmark run

# Run specific task(s)
agentmark run --task fix-type-error

# Run specific agent(s)
agentmark run --agent claude-code --agent aider

# Output formats
agentmark run --json           # JSON report
agentmark run --csv            # CSV for spreadsheets
agentmark run --md             # Markdown table

# Compare two previous runs
agentmark compare run-001 run-002

# List past runs
agentmark history
```

---

## Terminal Output (target UX)

```
$ agentmark run

 agentmark v0.1.0 — benchmarking 3 agents on 3 tasks
 repo: my-app (commit a1b2c3d)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Task 1/3: fix-type-error
 "Fix the TypeScript type error in src/auth/login.ts"
 validate: npx tsc --noEmit

   claude-code ····· PASS   15s   $0.08   4.2K tokens   2 LLM calls
   aider ··········· PASS   23s   $0.14   8.7K tokens   5 LLM calls
   codex ··········· PASS   31s   $0.21  12.1K tokens   8 LLM calls

 Task 2/3: add-pagination
 "Add offset/limit pagination to GET /api/users endpoint"
 validate: bun test test/api/users.test.ts

   claude-code ····· PASS   54s   $0.31  18.3K tokens   3 LLM calls
   aider ··········· FAIL   89s   $0.52  34.1K tokens  12 LLM calls
   codex ··········· PASS   72s   $0.44  28.9K tokens   9 LLM calls

 Task 3/3: write-tests
 "Write unit tests for src/payments/charge.ts"
 validate: bun test test/payments/

   claude-code ····· PASS   67s   $0.22  12.1K tokens   2 LLM calls
   aider ··········· PASS   94s   $0.38  22.4K tokens   7 LLM calls
   codex ··········· FAIL  110s   $0.61  41.2K tokens  14 LLM calls

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                Pass Rate   Avg Time   Avg Cost   Total Tokens   Efficiency
 claude-code    3/3 100%      45s       $0.20       34.6K        *****
 aider          2/3  67%      69s       $0.35       65.2K        ***
 codex          2/3  67%      71s       $0.42       82.2K        **

 Winner: claude-code (highest pass rate, lowest cost, fewest tokens)

 Full report saved to .agentmark/runs/2025-02-25-001.json
```

---

## Tech Stack

| Component | Choice | Reason |
|---|---|---|
| Language | Python 3.11+ | AI/ML audience lives in Python; PyPI reach |
| CLI framework | `click` | Mature, composable, well-documented |
| Terminal UI | `rich` | Beautiful tables, progress bars, panels |
| Config | `pyyaml` | Standard for YAML parsing |
| Isolation | `git worktree` via subprocess | Clean, fast, built into git |
| Package manager | `uv` | Fast installs, modern Python tooling |
| Testing | `pytest` | Standard Python testing |
| Build/publish | `hatch` or `flit` | Simple pyproject.toml → PyPI |

---

## Agent Adapters — How Each Works

### Claude Code
```python
command: "claude --print --max-turns 10 '{prompt}'"
# Token/cost parsing: claude outputs "Total tokens: X" and "Total cost: $Y"
# in its stderr/summary output
```

### Aider
```python
command: "aider --message '{prompt}' --yes-always --no-git"
# Token/cost parsing: aider outputs token counts and cost per session
# in its final summary. Also check ~/.aider/usage.json
```

### Codex
```python
command: "codex --quiet '{prompt}'"
# Token/cost parsing: codex reports usage in its output
```

### Custom agents
Users add any agent by providing:
- A shell command with `{prompt}` placeholder
- Optionally, a regex pattern to extract tokens/cost from output

---

## Build Plan (MVP in 4 weeks)

### Week 1: Core Framework
- [ ] Project scaffolding (pyproject.toml, src layout, CI)
- [ ] bench.yaml parser + validation (pydantic models)
- [ ] Git worktree sandbox (create, cleanup, error handling)
- [ ] Core runner loop (sequential: task × agent matrix)
- [ ] Validation runner (execute check command, capture exit code)
- [ ] Basic wall-time metrics

### Week 2: Agent Adapters + Metrics
- [ ] Base agent adapter interface
- [ ] Claude Code adapter (command + output parsing)
- [ ] Aider adapter (command + output parsing)
- [ ] Codex adapter (command + output parsing)
- [ ] Metrics collection: time, tokens, cost, LLM calls, pass/fail
- [ ] Run history storage (.agentmark/runs/*.json)

### Week 3: Terminal Output + Polish
- [ ] Rich reporter: per-task results table
- [ ] Rich reporter: summary table with winner
- [ ] JSON/CSV/Markdown export
- [ ] `agentmark init` command (generate sample bench.yaml)
- [ ] `agentmark history` command
- [ ] Error handling: agent timeout, crash recovery, partial results
- [ ] Parallel task execution (optional: run agents concurrently)

### Week 4: Launch Prep
- [ ] README with hero GIF (asciinema/vhs recording)
- [ ] Example bench.yaml files for common stacks (Node, Python, Go)
- [ ] Blog post: "I Benchmarked 3 AI Agents on My Codebase — Here's What I Found"
- [ ] PyPI publish (`pip install agentmark`)
- [ ] Homebrew formula (stretch goal)
- [ ] Submit to: Hacker News, r/programming, r/MachineLearning, Twitter

---

## Viral Launch Strategy

### Content that drives stars

1. **Hero screenshot/GIF** — The terminal comparison table IS the marketing.
   Must look beautiful. Record with `vhs` (charm.sh/vhs).

2. **Blog post with real data** — Run agentmark on a real project (your own
   qmd repo works). Show actual cost/time/pass-rate differences. Real
   numbers >> hypothetical examples.

3. **Twitter thread** — "I built a tool that benchmarks AI coding agents
   on your own codebase. Here's what I found when I ran Claude Code vs
   Aider vs Codex on my project:" + screenshot of results table.

4. **Hacker News** — "Show HN: agentmark — benchmark AI coding agents
   on your codebase" + link to repo with great README.

### Growth flywheel

```
Developer finds agentmark
    → runs it on their codebase
    → screenshots results
    → posts on Twitter/Reddit ("Claude beat GPT on my code!")
    → followers see it, try it themselves
    → more screenshots, more posts
    → repeat
```

### Name candidates (finalize before launch)

- `agentmark` — benchmark + agent. Clean, memorable.
- `pitbench` — agents competing in a pit
- `codepit` — code arena
- `benchit` — action-oriented

Check PyPI + GitHub availability before committing.

---

## Future Roadmap (post-MVP)

### v0.2 — Richer Metrics
- Agent strategy classification (reactive vs programmatic)
- File I/O tracking (which files did the agent read/write?)
- Diff quality scoring (how clean is the generated code?)
- Retry/backtrack detection (did the agent undo its own changes?)

### v0.3 — Community Features
- `agentmark share` — upload results to a public leaderboard
- Leaderboard website showing aggregate results across projects
- Compare by language, framework, task type

### v0.4 — Advanced Execution
- Parallel agent runs (run all agents concurrently)
- Statistical significance (run N times, report mean + stddev)
- Cost budget limits ("stop if agent exceeds $1")
- Custom scoring functions (weighted: 60% pass, 20% speed, 20% cost)

### v0.5 — Ecosystem
- GitHub Action: run agentmark in CI on every PR
- VS Code extension: run benchmarks from editor
- Agent plugin system: agents self-register with agentmark
- MCP integration: expose benchmark results as MCP resources

---

## Success Metrics

| Metric | Target (3 months) |
|---|---|
| GitHub stars | 1,000+ |
| PyPI installs | 5,000+ |
| Supported agents | 5+ (claude-code, aider, codex, cline, copilot-cli) |
| Blog/tweet mentions | 50+ |
| Contributors | 10+ |

---

## References

- ActionEngine paper: https://arxiv.org/abs/2602.20502
- SWE-bench: https://www.swebench.com/
- THUDM/AgentBench: https://github.com/THUDM/AgentBench
- jadbox/codeagentbench: https://github.com/jadbox/codeagentbench
- Terminal-Bench: https://www.tbench.ai/
- Codex Arena Mode: https://openai.com/index/introducing-codex/
- Aider leaderboard: https://aider.chat/docs/leaderboards/
- Rich library: https://github.com/Textualize/rich
- VHS (terminal GIF recorder): https://github.com/charmbracelet/vhs
