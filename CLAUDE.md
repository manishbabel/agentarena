# agentrace — Project Guide

## What Is This?
An open-source Python CLI to benchmark AI coding agents (Claude Code, Aider, Codex, etc.) on YOUR codebase with YOUR tasks. Produces terminal comparison reports (pass/fail, time, cost, tokens, LLM calls). "The Hyperfine of AI coding agents."

**Repo:** https://github.com/manishbabel/agentrace
**PyPI name:** `agentrace` (`pip install agentrace`)

## Full Plan
See `plan.md` for complete architecture, research foundation, viral strategy, and roadmap.

## Tech Stack
- Python 3.11+, click (CLI), rich (terminal UI), pyyaml (config), uv (package manager), pytest (testing), hatch (build/publish)
- Isolation via `git worktree` (subprocess)
- No LLM calls in agentrace itself — pure orchestration

## Project Structure
```
agentrace/
├── pyproject.toml
├── src/agentrace/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point (click)
│   ├── config.py            # Parse bench.yaml (pydantic models)
│   ├── sandbox.py           # Git worktree create/cleanup
│   ├── runner.py            # Core benchmark loop (task x agent matrix)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract agent interface
│   │   ├── claude_code.py   # claude --print adapter
│   │   ├── aider.py         # aider --message adapter
│   │   └── codex.py         # codex adapter
│   ├── metrics.py           # Token/cost/time collection + parsing
│   ├── validator.py         # Run validation commands, check exit codes
│   └── reporter.py          # Rich terminal output (tables, summary)
├── tests/
└── examples/bench.yaml
```

## Build Phases (MVP)

### Phase 1 — Core Framework (Week 1)
1. Project scaffolding (pyproject.toml, src layout, CI) — DONE
2. bench.yaml parser + validation (pydantic models) → `config.py` — DONE
3. Git worktree sandbox (create, cleanup, error handling) → `sandbox.py` — DONE
4. Core runner loop (sequential: task x agent matrix) → `runner.py`
5. Validation runner (execute check command, capture exit code) → `validator.py` — DONE
6. Basic wall-time metrics → `metrics.py` — DONE

### Phase 2 — Agent Adapters + Metrics (Week 2)
7. Base agent adapter interface → `agents/base.py` — IN PROGRESS
8. Claude Code adapter → `agents/claude_code.py`
9. Aider adapter → `agents/aider.py`
10. Codex adapter → `agents/codex.py`
11. Full metrics collection: time, tokens, cost, LLM calls, pass/fail
12. Run history storage → `.agentrace/runs/*.json`

### Phase 3 — Terminal Output + Polish (Week 3)
13. Rich reporter: per-task results table → `reporter.py`
14. Rich reporter: summary table with winner
15. JSON/CSV/Markdown export
16. `agentrace init` command
17. `agentrace history` command
18. Error handling: agent timeout, crash recovery, partial results
19. Parallel task execution (optional)

### Phase 4 — Launch Prep (Week 4)
20. README with hero GIF
21. Example bench.yaml files for common stacks
22. Blog post with real benchmark data
23. PyPI publish (`pip install agentrace`)
24. Submit to HN, Reddit, Twitter

## Key Design Rules
- Agents are **black boxes** — interact only via CLI, no SDK integration
- **Git worktrees** for isolation — clean copy per run, automatic cleanup
- **Validation is user-defined** — shell command, pass = exit code 0
- **Metrics from stdout parsing** — each adapter extracts tokens/cost from agent output
- **Zero AI cost** to run agentrace itself

## Config Format
Tasks + agents defined in `bench.yaml` at repo root. See `plan.md` for full schema.

## Current Status
- [x] Phase 1: scaffolding, config, sandbox, validator, metrics — DONE
- [x] Phase 2: agent (config-driven regex, no per-agent files) — DONE
- [x] Phase 3: reporter (Rich tables + JSON/CSV/MD export) + CLI (run, init) — DONE
- [ ] Phase 4: launch prep (README GIF, PyPI publish, blog post)

## MVP is complete. 81 tests pass. CLI works end-to-end.
