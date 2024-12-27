import pytest
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Dict
from backend.application.interfaces.iartifact_repository import IArtifactRepository
from backend.domain.models import DomainCompiledMultifact

def test_iartifact_repository_is_abstract():
    """
    Instantiating IArtifactRepository directly should raise TypeError
    because it has unimplemented abstract methods.
    """
    with pytest.raises(TypeError):
        IArtifactRepository() #type: ignore


def test_iartifact_repository_minimal_subclass():
    """
    Define a minimal subclass that implements all required methods,
    ensuring we can instantiate it without errors.
    """
    class MinimalArtifactRepo(IArtifactRepository):
        def get_artifact_by_id(self, artifact_id: int) -> Optional[DomainCompiledMultifact]:
            return None

        def update_artifact_code(self, artifact_id: int, new_code: str, valid: bool) -> None:
            pass

    repo = MinimalArtifactRepo()
    assert repo is not None


