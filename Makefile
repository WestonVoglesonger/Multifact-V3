.PHONY: install test lint docs clean build publish

install:
	pip install -e ".[dev,docs]"
	pre-commit install

test:
	pytest --cov=backend

lint:
	black backend/
	flake8 backend/
	mypy backend/

docs:
	cd docs && python make.py

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

build:
	python -m build

publish:
	python -m twine upload dist/*

init-db:
	multifact-db

dev:
	uvicorn backend.main:app --reload --port 8000

format:
	black backend/

typecheck:
	mypy backend/

benchmark:
	cd tools/benchmark && python benchmark_all_models.py 