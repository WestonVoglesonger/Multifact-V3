# Contributing to SNC

Thank you for your interest in contributing to SNC! This guide will help you get started.

## Development Setup

1. Fork and clone the repository:

```bash
git clone https://github.com/yourusername/snc.git
cd snc
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:

```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks:

```bash
pre-commit install
```

## Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for style guide enforcement
- **mypy** for type checking

Run all checks with:

```bash
# Format code
black .
isort .

# Run linters
flake8
mypy snc
```

## Testing

We use pytest for testing. Write tests for all new features:

```python
# tests/test_feature.py
def test_new_feature():
    # Arrange
    input_data = ...

    # Act
    result = feature_function(input_data)

    # Assert
    assert result == expected_output
```

Run tests with:

```bash
pytest
pytest --cov=snc  # With coverage
```

## Documentation

We use Sphinx for documentation:

1. Write docstrings in Google style:

```python
def function_name(param1: str, param2: int) -> bool:
    """Short description.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: Description of when this error occurs
    """
```

2. Build documentation:

```bash
cd docs
make html
```

## Pull Request Process

1. Create a feature branch:

```bash
git checkout -b feature/your-feature-name
```

2. Make your changes:

   - Write tests
   - Update documentation
   - Follow code style guidelines

3. Commit your changes:

```bash
git add .
git commit -m "feat: Add new feature"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

4. Push and create PR:

```bash
git push origin feature/your-feature-name
```

5. Wait for review

## Release Process

1. Version bumping:

   - Update version in setup.py
   - Update CHANGELOG.md
   - Create release commit

2. Create release:
   - Tag version
   - Push to PyPI
   - Update documentation

## Code Review Guidelines

When reviewing PRs, check for:

1. **Functionality**

   - Does it work as intended?
   - Are edge cases handled?

2. **Code Quality**

   - Is it readable and maintainable?
   - Does it follow our style guide?

3. **Testing**

   - Are there sufficient tests?
   - Do all tests pass?

4. **Documentation**
   - Are changes documented?
   - Are docstrings complete?

## Getting Help

- Join our Discord server
- Check existing issues
- Ask questions in discussions
- Read the documentation
