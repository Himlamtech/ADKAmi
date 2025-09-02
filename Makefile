PY=uv run python
UV=uv

.PHONY: setup sync run dev lint format type test hooks hooks-strict hooks-update clean

setup:
	$(UV) sync
	$(UV) run pre-commit install

sync:
	$(UV) sync

run:
	$(UV) run uvicorn app.main:app --host 0.0.0.0 --port 2003 --reload

dev: run

lint:
	$(UV) run ruff check app tests
	$(UV) run black --check .
	$(UV) run isort --check-only .

format:
	$(UV) run ruff check app tests --fix
	$(UV) run ruff format .
	$(UV) run isort .

type:
	$(UV) run mypy app

test:
	$(UV) run pytest

# Auto-fix formatting (lenient mode)
hooks:
	$(UV) run pre-commit run --all-files

# Strict checking (mypy, bandit, etc.)
hooks-strict:
	./scripts/check-strict.sh

hooks-update:
	$(UV) run pre-commit autoupdate
	$(UV) add --dev --upgrade pre-commit

clean:
	find . -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache