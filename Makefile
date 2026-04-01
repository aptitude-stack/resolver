UV ?= UV_CACHE_DIR=.uv-cache uv

.PHONY: run debug test lint format typecheck

run:
	@printf "\033[1;36m==>\033[0m \033[1mStarting Aptitude client\033[0m\n"
	@printf "\033[0;36m  Mode:\033[0m  TUI with CLI fallback\n"
	@printf "\033[0;36m  Stop:\033[0m  Ctrl+C\n\n"
	@$(UV) run python -m aptitude_client.interfaces.cli.main

debug:
	@printf "\033[1;36m==>\033[0m \033[1mStarting Aptitude client in debug mode\033[0m\n"
	@printf "\033[0;36m  Mode:\033[0m  Python dev mode\n"
	@printf "\033[0;36m  Stop:\033[0m  Ctrl+C\n\n"
	@PYTHONDEVMODE=1 $(UV) run python -m aptitude_client.interfaces.cli.main

test:
	$(UV) run --extra dev python -m pytest -q

lint:
	$(UV) run --extra dev ruff check src tests

format:
	$(UV) run --extra dev ruff format src tests

typecheck:
	$(UV) run --extra dev python -m mypy src tests
