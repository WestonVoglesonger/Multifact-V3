from typing import Optional
from snc.domain.models import DomainCompiledMultifact
from abc import ABC, abstractmethod


class IArtifactRepository(ABC):
    """
    Interface for the ArtifactRepository.
    """

    @abstractmethod
    def get_artifact_by_id(self, artifact_id: int) -> Optional[DomainCompiledMultifact]:
        pass

    @abstractmethod
    def update_artifact_code(
        self, artifact_id: int, new_code: str, valid: bool
    ) -> None:
        pass
