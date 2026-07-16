.PHONY: setup run test lint typecheck build package docs clean

setup:
	uv sync --extra dev

run:
	uv run vaydeer-studio --mock jp1011

test:
	uv run pytest

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

build:
	uv build

package:
	./scripts/package.sh

docs:
	./scripts/check-docs.sh

clean:
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache
