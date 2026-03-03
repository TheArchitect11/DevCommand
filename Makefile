.PHONY: install dev lint format type-check test test-cov clean build run

# --- Setup ---
install:
	pip install -e .

dev:
	pip install -e ".[dev]"

# --- Quality ---
lint:
	ruff check devcommand/ tests/

format:
	ruff format devcommand/ tests/

type-check:
	mypy devcommand/

# --- Testing ---
test:
	pytest --tb=short -q

test-cov:
	pytest --cov=devcommand --cov-report=term-missing --cov-report=html

# --- Build ---
build:
	python -m build

clean:
	rm -rf dist/ build/ *.egg-info .coverage htmlcov/ .mypy_cache/ .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# --- Run ---
run:
	devcmd

run-debug:
	devcmd --debug

run-profile:
	devcmd --debug --profile
