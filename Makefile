UV ?= UV_CACHE_DIR=.uv-cache uv
REPOSITORY ?= pypi
PUBLISH_DIST_DIR ?= .build-publish-dist

ifeq ($(REPOSITORY),pypi)
PUBLISH_URL := https://upload.pypi.org/legacy/
CHECK_URL := https://pypi.org/simple/
endif

ifeq ($(REPOSITORY),testpypi)
PUBLISH_URL := https://test.pypi.org/legacy/
CHECK_URL := https://test.pypi.org/simple/
endif

.PHONY: run debug demo test test-cov lint format typecheck package publish build-publish

run:
	@printf "\033[1;36m==>\033[0m \033[1mStarting Aptitude\033[0m\n"
	@printf "\033[0;36m  Mode:\033[0m  TUI with CLI fallback\n"
	@printf "\033[0;36m  Stop:\033[0m  Ctrl+C\n\n"
	@PYTHONPATH=src .venv/bin/python -m aptitude.interfaces.cli.main

debug:
	@printf "\033[1;36m==>\033[0m \033[1mStarting Aptitude in debug mode\033[0m\n"
	@printf "\033[0;36m  Mode:\033[0m  Python dev mode\n"
	@printf "\033[0;36m  Stop:\033[0m  Ctrl+C\n\n"
	@PYTHONPATH=src PYTHONDEVMODE=1 .venv/bin/python -m aptitude.interfaces.cli.main

demo:
	@test -f .env || { \
		printf "\033[1;31merror:\033[0m missing .env file. Copy .env.example to .env and fill in your local values.\n"; \
		exit 1; \
	}
	@printf "\033[1;36m==>\033[0m \033[1mRunning Aptitude demo TUI\033[0m\n"
	@printf "\033[0;36m  Suggest:\033[0m Postman Primary Skill\n"
	@printf "\033[0;36m  Env:\033[0m    .env\n\n"
	@set -a; \
	. ./.env; \
	set +a; \
	PYTHONPATH=src .venv/bin/python -m aptitude.interfaces.cli.main

test:
	$(UV) run --extra dev python -m pytest -q

test-cov:
	$(UV) run --extra dev python -m pytest --cov=src/aptitude --cov-branch --cov-report=term-missing -q

lint:
	$(UV) run --extra dev ruff check src tests

format:
	$(UV) run --extra dev ruff format src tests

typecheck:
	$(UV) run --extra dev python -m mypy src tests

package:
	$(UV) build --no-sources

publish: build-publish

build-publish:
	@test -n "$(PYPI_API_TOKEN)" || { \
		printf "\033[1;31merror:\033[0m missing PYPI_API_TOKEN environment variable.\n"; \
		exit 1; \
	}
	@test -n "$(PUBLISH_URL)" || { \
		printf "\033[1;31merror:\033[0m unsupported REPOSITORY '%s'. Use 'pypi' or 'testpypi'.\n" "$(REPOSITORY)"; \
		exit 1; \
	}
	@printf "\033[1;36m==>\033[0m \033[1mBuilding Aptitude distributions\033[0m\n"
	@printf "\033[0;36m  Output:\033[0m %s\n" "$(PUBLISH_DIST_DIR)"
	@printf "\033[0;36m  Target:\033[0m %s\n\n" "$(REPOSITORY)"
	@$(UV) build --no-sources --clear --out-dir "$(PUBLISH_DIST_DIR)"
	@printf "\033[1;36m==>\033[0m \033[1mPublishing Aptitude distributions\033[0m\n"
	@printf "\033[0;36m  Upload:\033[0m %s\n" "$(PUBLISH_URL)"
	@printf "\033[0;36m  Check:\033[0m  %s\n\n" "$(CHECK_URL)"
	@UV_PUBLISH_TOKEN="$(PYPI_API_TOKEN)" \
	$(UV) publish \
		--trusted-publishing never \
		--publish-url "$(PUBLISH_URL)" \
		--check-url "$(CHECK_URL)" \
		"$(PUBLISH_DIST_DIR)"/*
