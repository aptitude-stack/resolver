# Development Setup

## Runtime

- Python `>=3.9`
- `uv` for environment and task execution

## Install Dependencies

```bash
uv sync --extra dev
```

## Common Commands

Use the provided `Makefile` for everyday work:

```bash
make run
make debug
make test
make lint
make format
make typecheck
```

Direct `uv` equivalents:

```bash
UV_CACHE_DIR=.uv-cache uv run --extra dev pytest -q
UV_CACHE_DIR=.uv-cache uv run --extra dev ruff check src tests
UV_CACHE_DIR=.uv-cache uv run --extra dev ruff format src tests
UV_CACHE_DIR=.uv-cache uv run --extra dev python -m mypy src tests
```

## Entry Points

- verified repo-local entrypoint: `PYTHONPATH=src .venv/bin/python -m aptitude_resolver.interfaces.cli.main`
- logical console command name: `aptitude`

Running the module entrypoint with no arguments currently enters the Textual TUI and falls back to CLI subcommands when arguments are present.
