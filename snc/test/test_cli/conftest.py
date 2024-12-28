"""
Pytest configuration for CLI tests.
"""

import os
from typing import Dict, Generator, Optional
import pytest
from pathlib import Path
from snc.domain.repositories.artifact import ArtifactRepository
from snc.domain.models.artifact import Artifact


class MockArtifactRepository(ArtifactRepository):
    """Mock artifact repository for testing."""

    def __init__(self) -> None:
        """Initialize mock repository."""
        self.artifacts: Dict[str, Artifact] = {}

    def get_artifact_by_id(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by ID."""
        return self.artifacts.get(artifact_id)

    def update_artifact_code(self, artifact_id: str, code: str) -> None:
        """Update artifact code."""
        if artifact_id in self.artifacts:
            self.artifacts[artifact_id].code = code


@pytest.fixture
def mock_artifact_repo() -> MockArtifactRepository:
    """Provide a mock artifact repository."""
    return MockArtifactRepository()


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Provide a clean environment for tests."""
    # Store original environment
    original_env: Dict[str, str] = dict(os.environ)

    # Clear relevant environment variables
    env_vars = [
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
        "LOG_LEVEL",
        "LOG_FILE",
    ]
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def test_env_file(tmp_path: Path) -> Path:
    """Create a test environment file."""
    env_file = tmp_path / ".env"
    env_content = """
    LOG_LEVEL=INFO
    DATABASE_URL=sqlite:///test.db
    OPENAI_API_KEY=sk-1234567890abcdef1234567890abcdef1234567890abcdef1234
    GROQ_API_KEY=gsk_1234567890abcdef1234567890abcdef1234567890abcdef1234
    LOG_FILE=logs/test.log
    """
    env_file.write_text(env_content.strip())
    return env_file


@pytest.fixture
def test_narrative_file(tmp_path: Path) -> Path:
    """Create a test narrative file."""
    narrative_file = tmp_path / "test.txt"
    narrative_content = """
    [Component:Button]
    Create a reusable button component.

    [Component:Form]
    Create a form that [REF:Button] uses the button component.

    [Scene:LoginPage]
    Create a login page that [REF:Form] uses the form and [REF:Button] the button.
    """
    narrative_file.write_text(narrative_content.strip())
    return narrative_file
