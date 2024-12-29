.PHONY: install test lint docs clean build publish

install:
	pip install -e ".[dev,test,docs]"
	pre-commit install

test:
	pytest --cov=snc --cov-report=term-missing

lint:
	black .
	mypy snc
	pre-commit run --all-files

docs:
	cd docs && make html

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	cd docs && make clean

build: clean
	python -m build

publish: build
	twine check dist/*
	twine upload dist/*

dev-setup: install
	pip install -e ".[dev]"
	pre-commit install
	python -m snc.script.create_database

benchmark:
	python -m snc.benchmark.run_benchmarks
