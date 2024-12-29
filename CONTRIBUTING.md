# Contributing to System Narrative Compiler

We love your input! We want to make contributing to SNC as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## We Develop with Github
We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Development Process
We use GitHub to sync code to and from our internal repository. We'll use GitHub
to track issues and feature requests, as well as accept pull requests.

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/westonvogelsong/snc-v3.git
cd snc-v3
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Running Tests
```bash
pytest
```

For coverage report:
```bash
pytest --cov=snc
```

## Code Style
- We use `black` for Python code formatting
- We use `mypy` for type checking
- We use `flake8` for linting

## Pull Request Process

1. Update the README.md with details of changes to the interface, if applicable.
2. Update the CHANGELOG.md with notes on your changes.
3. The PR will be merged once you have the sign-off of at least one other developer.

## Any contributions you make will be under the MIT Software License
In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issue tracker](https://github.com/westonvogelsong/snc-v3/issues)
We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/westonvogelsong/snc-v3/issues/new); it's that easy!

## License
By contributing, you agree that your contributions will be licensed under its MIT License.
