# aptitude-client

![Python Version](https://img.shields.io/badge/python-3.9+-3776AB?logo=python)
![License](https://img.shields.io/github/license/y0ncha/aptitude-client)
![Last Commit](https://img.shields.io/github/last-commit/y0ncha/aptitude-client)
![Issues](https://img.shields.io/github/issues/y0ncha/aptitude-client)
![Status](https://img.shields.io/badge/status-active--development-blue)

Aptitude Client is the runtime-facing client/orchestration service for the Aptitude ecosystem.  
It translates runtime requests (prompt/tool calls) into execution plans while preserving deterministic repository contracts.

The repository provides:

- Runtime request normalization
- Deterministic resolve integration via repository APIs
- Plugin-driven security/policy/overlap checks
- Execution plan assembly with trace metadata
- Client-local cache and observability surfaces

---

## Design Principles

- Repository contracts are authoritative and versioned
- Runtime orchestration stays deterministic and auditable
- Client and repository responsibilities stay strictly separated
- Plugin outcomes are explicit and traceable
- Interfaces remain transport-agnostic (MCP/CLI, optional HTTP adapters)

---

## Architecture (High-Level)

Runtime Clients (MCP / CLI / HTTP Adapter)  
→ Request Normalization  
→ Repository Resolve API (contract-only)  
→ Plugin Chain (Security + Policy + Overlap)  
→ Execution Plan + Trace Output  
→ Cache + Observability

---

## Current Status

The project is under active development and currently at foundation scaffold stage (`main.py`) with client implementation planned from PRD.

Roadmap and implementation references:

- [Overview](docs/overview.md)
- [Client PRD](docs/client-prd.md)
- [Scope and Boundary](docs/scope.md)

---

## Planned Stack

- API: FastAPI
- Runtime: Python 3.9+
- Server: Uvicorn
- Package/deps: `uv` (recommended) or `pip`
- Testing/quality (planned): pytest, ruff, mypy

---

## Getting Started

### Requirements

- Python 3.9+
- `uv` (recommended) or `pip`

### Install

Using `uv`:

```bash
uv sync
```

Using `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run locally

```bash
uvicorn main:app --reload
```

Server URL: `http://127.0.0.1:8000`

### Smoke test

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/hello/User
```
