.PHONY: lint format lint-python format-python

lint: lint-python

format: format-python

lint-python:
	ruff check backend packages/sdk-python

format-python:
	ruff format backend packages/sdk-python
