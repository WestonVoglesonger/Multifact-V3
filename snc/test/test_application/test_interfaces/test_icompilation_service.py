import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from snc.application.interfaces.icompilation_service import ICompilationService
from snc.domain.models import DomainCompiledMultifact
from snc.domain.model_types import CompilationResult


def test_icompilation_service_is_abstract():
    with pytest.raises(
        TypeError, match="Can't instantiate abstract class ICompilationService"
    ):
        ICompilationService()  # type: ignore


def test_icompilation_service_minimal_subclass():
    class MinimalCompilationService(ICompilationService):
        def compile(self, code: str) -> CompilationResult:
            return CompilationResult(
                code=code,
                valid=True,
                errors=[],
                created_at=datetime.now(),
                cache_hit=False,
                score=0.85,
                feedback="Code looks good and follows best practices",
            )

        def compile_multifact(
            self, multifact: DomainCompiledMultifact
        ) -> CompilationResult:
            return CompilationResult(
                code=multifact.code,
                valid=True,
                errors=[],
                created_at=datetime.now(),
                cache_hit=False,
                score=0.85,
                feedback="Code looks good and follows best practices",
            )

    service = MinimalCompilationService()
    result = service.compile("test code")
    assert result.valid
    assert result.code == "test code"
    assert len(result.errors) == 0

    multifact = DomainCompiledMultifact(
        artifact_id=123,
        ni_token_id=1,
        language="ts",
        framework="angular",
        code="test multifact code",
        valid=True,
        cache_hit=False,
        created_at=datetime.now(),
        score=0.85,
        feedback="Code looks good and follows best practices",
    )
    result = service.compile_multifact(multifact)
    assert result.valid
    assert result.code == "test multifact code"
    assert len(result.errors) == 0
