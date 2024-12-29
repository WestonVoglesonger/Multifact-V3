"""Interface for artifact repository operations."""

from abc import ABC, abstractmethod
from typing import Optional
from snc.domain.models import DomainCompiledMultifact


class IArtifactRepository(ABC):
    """Repository interface for managing compiled artifacts."""

    @abstractmethod
    def get_artifact_by_id(
        self, artifact_id: int
    ) -> Optional[DomainCompiledMultifact]:
        """Get an artifact by its ID.

        Args:
            artifact_id: ID of the artifact to retrieve

        Returns:
            The artifact if found, None otherwise
        """
        pass

    @abstractmethod
    def update_artifact_code(
        self, artifact_id: int, new_code: str, valid: bool
    ) -> None:
        """Update the code and validity of an artifact.

        Args:
            artifact_id: ID of the artifact to update
            new_code: New code to set
            valid: Whether the new code is valid
        """
        pass
