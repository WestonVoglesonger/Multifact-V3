"""Artifact repository interface."""

from abc import ABC, abstractmethod
from typing import Optional
from snc.domain.models import DomainCompiledMultifact


class ArtifactRepository(ABC):
    """Interface for artifact repositories."""

    @abstractmethod
    def get_artifact_by_id(
        self, artifact_id: str
    ) -> Optional[DomainCompiledMultifact]:
        """Get artifact by ID."""
        pass

    @abstractmethod
    def update_artifact_code(self, artifact_id: str, code: str) -> None:
        """Update artifact code."""
        pass
