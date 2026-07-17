.PHONY: setup run test lint typecheck build package install-smoke docs clean

setup:
	uv sync --extra dev

run:
	uv run vaydeer-studio --mock jp1011

test:
	uv run pytest

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

typecheck:
	uv run mypy src

build:
	uv build

package:
	./scripts/package.sh

install-smoke:
	./scripts/test-install.sh

docs:
	./scripts/check-docs.sh
	uv run pytest -q tests/unit/test_release_metadata.py

clean:
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache
