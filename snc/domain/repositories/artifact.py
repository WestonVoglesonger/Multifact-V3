"""
Artifact repository interface.
"""

from abc import ABC, abstractmethod
from typing import Optional
from snc.domain.models.artifact import Artifact


class ArtifactRepository(ABC):
    """Interface for artifact repositories."""

    @abstractmethod
    def get_artifact_by_id(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by ID."""
        pass

    @abstractmethod
    def update_artifact_code(self, artifact_id: str, code: str) -> None:
        """Update artifact code."""
        pass
