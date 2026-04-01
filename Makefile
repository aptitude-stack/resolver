UV ?= UV_CACHE_DIR=.uv-cache uv

.PHONY: run debug test lint format typecheck package publish

run:
	@printf "\033[1;36m==>\033[0m \033[1mStarting Aptitude Resolver\033[0m\n"
	@printf "\033[0;36m  Mode:\033[0m  TUI with CLI fallback\n"
	@printf "\033[0;36m  Stop:\033[0m  Ctrl+C\n\n"
	@PYTHONPATH=src .venv/bin/python -m aptitude_resolver.interfaces.cli.main

debug:
	@printf "\033[1;36m==>\033[0m \033[1mStarting Aptitude Resolver in debug mode\033[0m\n"
	@printf "\033[0;36m  Mode:\033[0m  Python dev mode\n"
	@printf "\033[0;36m  Stop:\033[0m  Ctrl+C\n\n"
	@PYTHONPATH=src PYTHONDEVMODE=1 .venv/bin/python -m aptitude_resolver.interfaces.cli.main

test:
	$(UV) run --extra dev python -m pytest -q

lint:
	$(UV) run --extra dev ruff check src tests

format:
	$(UV) run --extra dev ruff format src tests

typecheck:
	$(UV) run --extra dev python -m mypy src tests

package:
	$(UV) build --no-sources

publish:
	@printf "\033[1;33mPublishing is handled by GitHub Actions trusted publishing.\033[0m\n"
	@printf "Create and push a version tag that matches v*.\n\n"
	@printf "Example:\n"
	@printf "  git tag v0.1.0\n"
	@printf "  git push origin v0.1.0\n"
