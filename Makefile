.PHONY: test lint format

test:
	python -m pytest

lint:
	python -m ruff check foresight tests scripts

format:
	python -m ruff format foresight tests scripts

