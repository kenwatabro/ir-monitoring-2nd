PYTHON := venv/bin/python
PYTEST  := $(PYTHON) -m pytest
RUFF    := $(PYTHON) -m ruff

.PHONY: install install-dev lint format test test-unit

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) check --fix .
	$(RUFF) format .

test-unit:
	$(PYTEST) tests/unit --maxfail=1 --disable-warnings -q

test: test-unit

db-init:
	$(PYTHON) -c "from src.db import get_connection; print('DB connection OK')"

db-psql:
	psql "$$PGURL"
