import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from backend.application.interfaces.icompilation_service import ICompilationService
from backend.domain.models import DomainCompiledMultifact

def test_icompilation_service_is_abstract():
    with pytest.raises(TypeError, match="Can't instantiate abstract class ICompilationService"):
        ICompilationService() # type: ignore


def test_icompilation_service_minimal_subclass():
    class MinimalCompilationService(ICompilationService):
        def compile_document(self, doc_id: int) -> dict:
            return {}

        def compile_token_with_dependencies(self, token_id: int, compiled_artifacts: dict) -> str:
            return "code"

        def compile_token(self, token_id: int) -> DomainCompiledMultifact:
            # In a real scenario, you'd return a real DomainCompiledMultifact
            return DomainCompiledMultifact(
                artifact_id=123,
                ni_token_id=token_id,
                language="ts",
                framework="angular",
                code="some code",
                valid=True,
                cache_hit=False,
                created_at=datetime.now(),
                score=0.85,
                feedback="Code looks good and follows best practices",
            )

        def mark_artifact_invalid(self, artifact_id: int) -> None:
            pass

        def update_artifact(self, artifact: DomainCompiledMultifact) -> None:
            pass

        def get_session(self) -> Session:
            return Session()

    service = MinimalCompilationService() 
    assert service.compile_document(1) == {}
    assert service.compile_token_with_dependencies(2, {}) == "code"

