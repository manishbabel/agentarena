# Contributing to agentrace

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/manishbabel/agentrace.git
cd agentrace

# Create a virtual environment and install dependencies
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest
```

## How to Contribute

1. **Fork** the repository
2. **Create a branch** for your feature or fix: `git checkout -b my-feature`
3. **Make your changes** and add tests
4. **Run tests** to make sure everything passes: `pytest`
5. **Commit** with a clear message
6. **Open a Pull Request** against `main`

## Adding a New Agent Adapter

1. Create a new file in `src/agentrace/agents/` (e.g., `my_agent.py`)
2. Subclass `BaseAgent` from `agents/base.py`
3. Implement `build_command()` and `parse_output()` methods
4. Add tests in `tests/`

## Code Style

- Follow existing patterns in the codebase
- Keep it simple — no over-engineering
- Write tests for new functionality

## Reporting Issues

Open an issue on GitHub with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
