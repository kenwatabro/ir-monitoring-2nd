# Repository Guidelines

## Project Structure & Module Organization
Python services and parsers live in `src/` with sub-packages:
- `src/ingest/` — EDINET ZIP download and DB loading
- `src/parser/` — XBRL parsing and financial summary extraction
- `src/query/` — time-series and screening queries
- `src/analytics/` — screeners and metrics
- `src/db/` — DB connection helpers

SQL schema lives in `ddl/`. Utility scripts (data repair, dedup, re-parse) live in `scripts/`. Tests live in `tests/unit/`.

## Build, Test, and Development Commands
```bash
# One-time setup
python -m venv venv
pip install -r requirements-dev.txt   # includes pytest and ruff

# Lint (ruff check + format check)
make lint

# Auto-fix formatting
make format

# Unit tests
make test-unit
# or directly:
venv/bin/python -m pytest tests/unit -q
```

There is no Docker-based integration test harness yet. DB-dependent tests require a running PostgreSQL instance configured via `.env`.

## Environment Setup
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```
Required variables: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (or `PGURL`).

## Coding Style & Naming Conventions
Ruff (configured in `ruff.toml`) enforces 120-character lines, double quotes, and POSIX endings. Keep modules lowercase with underscores, classes in CapWords, and functions in `snake_case`. Run `make format` before committing.

## Testing Guidelines
Pytest auto-discovers under `tests/`. Add files as `test_<feature>.py` with descriptive function names. Shared fixtures live in `tests/conftest.py`. DB-dependent tests should be guarded or use mocks so `make test-unit` runs without a live DB.

## Commit & Pull Request Guidelines
Follow Conventional Commits: `<type>(scope): imperative summary` (e.g. `fix(parser): handle empty XBRL tags`). Keep messages short and focused on the behavior change. Pull requests should note any schema or env changes.

## Configuration & Security
Never commit `.env` or credentials. Reference environment variables via `src/db/core.py` helpers. Schema changes should add a new file in `ddl/` (e.g. `003_...sql`).
