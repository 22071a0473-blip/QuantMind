.PHONY: test lint format

test:
	python -m pytest

lint:
	python -m ruff check quantmind tests scripts

format:
	python -m ruff format quantmind tests scripts

