# Repository Guidelines

## Project Structure & Module Organization
Python services, clients, and observability helpers sit in `src/` (`runner.py` wires API fetchers, parsers, and processors). SQL and schema artifacts live in `sql/`, `ddl/`, and `migrations/`, while orchestrated jobs stay in `flows/`. Configuration templates reside in `config/` plus `env.example`, docs and runbooks live in `docs/`, and automation scripts (database reset, importers, health checks) stay in `scripts/`. Tests, including the Docker-backed scenarios in `tests/integration/`, live under `tests/`.

## Build, Test, and Development Commands
After activating a virtualenv, run `make install-dev` to pull requirements. `make lint` executes `ruff check .` and `ruff format --check .`—fix issues before pushing. Use `make test/unit` for the fast pytest suite (`--maxfail=1 --disable-warnings`). Integration coverage runs via `make test/integration`, which launches `docker-compose.integration.yml`, seeds the DB with `scripts/reset_and_migrate_db.py`, executes `pytest -m integration tests/integration`, then tears down the stack. `make db/init` rebuilds the schema locally, `make db/psql` opens a shell pointed at `$PGURL`, and `make docker/build` packages the app image.

## Coding Style & Naming Conventions
Ruff (configured in `ruff.toml`) enforces 120-character lines, spaces for indentation, double quotes, and POSIX endings. Keep modules lowercase with underscores, classes in CapWords, and functions, fixtures, and metrics names in `snake_case`. Favor dependency injection via `config.py` helpers over globals and run Ruff in fix mode before committing to avoid automated review churn.

## Testing Guidelines
Pytest auto-discovers under `tests/`, so add files as `test_<feature>.py` with descriptive function names. Shared fixtures live in `tests/conftest.py`. Mark DB-dependent scenarios with `@pytest.mark.integration` and keep them under `tests/integration/` so they only run in the Compose harness. Every feature PR should add or update unit tests for unhappy paths and extend integration coverage whenever flows, SQL, or migrations change.

## Commit & Pull Request Guidelines
Follow the existing Conventional Commit pattern `<type>(scope): imperative summary` (examples: `feat(observability): track api metrics`, `docs: add star-schema runbook`). Keep messages short, present tense, and focused on the behavior change. Pull requests must describe intent, link related issues, note schema or env updates, and paste the commands you executed (`make lint`, `make test/unit`, etc.). Attach screenshots or sample payloads for user-facing updates.

## Configuration & Security Tips
Copy `env.example` to `.env`, fill credentials locally, and reference variables through `config/` utilities; never commit secrets. Database changes should update both migrations and any mirrored SQL under `resources/` to avoid drift. Ensure Docker Desktop or the Linux daemon is running before `make test/integration`.
