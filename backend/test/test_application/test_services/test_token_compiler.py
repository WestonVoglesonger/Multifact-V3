# tests/services/test_token_compiler.py

import pytest
from sqlalchemy.orm import Session
from backend.application.services.token_compiler import TokenCompiler
from backend.infrastructure.repositories.token_repository import TokenRepository
from backend.infrastructure.services.compilation_service import (
    ConcreteCompilationService,
)
from backend.infrastructure.validation.validation_service import (
    ConcreteValidationService,
)
from backend.application.services.code_evaluation_service import CodeEvaluationService
from backend.infrastructure.llm.model_factory import GroqModelType
from backend.infrastructure.llm.client_factory import ClientFactory
from backend.domain.models import DomainToken
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact
from backend.infrastructure.entities.ni_token import NIToken
from backend.application.services.token_diff_service import TokenDiffService
from datetime import datetime, timezone
from unittest.mock import MagicMock
from backend.test.test_application.test_services.fixtures import (
    patch_client_factory,
    mock_validation_service_success,
    mock_validation_service_failure,
    mock_llm_client,
)


def test_token_compiler_compile_success(
    db_session: Session,
    patch_client_factory: MagicMock,
    mock_validation_service_success: MagicMock,
):
    """
    Test that compiling a token with valid code creates an artifact marked as valid.
    """
    # Find the token with content "Should compile content."
    should_compile_token = (
        db_session.query(NIToken)
        .filter(NIToken.content == "Should compile content.")
        .first()
    )
    assert (
        should_compile_token
    ), "Token 'Should compile content.' should exist in demo data."
    token_id = should_compile_token.id

    # Get DomainToken
    token_repo = TokenRepository(db_session)
    domain_token = token_repo.get_token_by_id(token_id)
    assert domain_token, "Token should be fetched from repository."

    # Setup services
    compilation_service = ConcreteCompilationService(db_session)
    validation_service = ConcreteValidationService(db_session)
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)
    evaluation_service = CodeEvaluationService(llm_client)
    compiler = TokenCompiler(
        compilation_service, validation_service, evaluation_service
    )

    # Call compile_and_validate
    compiler.compile_and_validate([domain_token], llm_client, revalidate=True)

    # Check artifact
    artifact = (
        db_session.query(CompiledMultifact)
        .filter(
            CompiledMultifact.ni_token_id == token_id, CompiledMultifact.valid == True
        )
        .first()
    )
    assert artifact, "Artifact should have been created."
    assert artifact.valid == True, "Artifact should be marked as valid."
    assert artifact.cache_hit == False, "Artifact should not be a cache hit."


def test_token_compiler_compile_fail(
    db_session: Session,
    patch_client_factory: MagicMock,
    mock_validation_service_failure: MagicMock,
):
    """
    Test that compiling a token with invalid code creates an artifact marked as invalid.
    """
    # Find the token with content "Will fail content."
    will_fail_token = (
        db_session.query(NIToken)
        .filter(NIToken.content == "Will fail content.")
        .first()
    )
    assert will_fail_token, "Token 'Will fail content.' should exist in demo data."
    token_id = will_fail_token.id

    # Get DomainToken
    token_repo = TokenRepository(db_session)
    domain_token = token_repo.get_token_by_id(token_id)
    assert domain_token, "Token should be fetched from repository."

    # Setup services
    compilation_service = ConcreteCompilationService(db_session)
    validation_service = ConcreteValidationService(db_session)
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)
    evaluation_service = CodeEvaluationService(llm_client)
    compiler = TokenCompiler(
        compilation_service, validation_service, evaluation_service
    )

    # Call compile_and_validate
    compiler.compile_and_validate([domain_token], llm_client, revalidate=True)

    # Check artifact
    artifact = (
        db_session.query(CompiledMultifact)
        .filter(
            CompiledMultifact.ni_token_id == token_id, CompiledMultifact.valid == False
        )
        .first()
    )
    assert artifact, "Artifact should exist even if compilation failed."
    assert (
        artifact.valid == False
    ), "Artifact should be marked as invalid due to compilation failure."
    assert artifact.cache_hit == False, "Artifact should not be a cache hit."


def test_token_compiler_no_id_raises_error(
    db_session: Session, patch_client_factory: MagicMock
):
    """
    Attempting to compile a token with no ID should raise ValueError.
    """
    # Create a DomainToken in memory (not in DB)
    domain_token = DomainToken(
        id=None,
        token_uuid="fake-uuid",
        token_type="scene",
        content="No ID token",
        hash=TokenDiffService._compute_hash("No ID token"),
    )

    # Setup services
    compilation_service = ConcreteCompilationService(db_session)
    validation_service = ConcreteValidationService(db_session)
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)
    evaluation_service = CodeEvaluationService(llm_client)
    compiler = TokenCompiler(
        compilation_service, validation_service, evaluation_service
    )

    # Get LLM client (mocked)
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)

    # Expect ValueError
    with pytest.raises(ValueError, match="Token ID cannot be None"):
        compiler.compile_and_validate([domain_token], llm_client, revalidate=False)


def test_token_compiler_cache_hit(
    db_session: Session,
    patch_client_factory: MagicMock,
    mock_validation_service_success: MagicMock,
):
    """
    Test that compiling a token with an existing cache_hit=True artifact does not create a new artifact.
    """
    # Find the token with content "Should compile content."
    should_compile_token = (
        db_session.query(NIToken)
        .filter(NIToken.content == "Should compile content.")
        .first()
    )
    assert (
        should_compile_token
    ), "Token 'Should compile content.' should exist in demo data."
    token_id = should_compile_token.id

    # Create an artifact with cache_hit=True
    existing_artifact = CompiledMultifact(
        ni_token_id=token_id,
        language="typescript",
        framework="angular",
        code="console.log('Hello World');",
        valid=True,
        cache_hit=True,
        token_hash=should_compile_token.hash,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(existing_artifact)
    db_session.commit()

    # Get DomainToken
    token_repo = TokenRepository(db_session)
    domain_token = token_repo.get_token_by_id(token_id)
    assert domain_token, "Token should be fetched from repository."

    # Setup services
    compilation_service = ConcreteCompilationService(db_session)
    validation_service = ConcreteValidationService(db_session)
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)
    evaluation_service = CodeEvaluationService(llm_client)
    compiler = TokenCompiler(
        compilation_service, validation_service, evaluation_service
    )

    # Call compile_and_validate with revalidate=False
    compiler.compile_and_validate([domain_token], llm_client, revalidate=False)

    # Ensure no new artifact is created
    artifacts = (
        db_session.query(CompiledMultifact)
        .filter(CompiledMultifact.ni_token_id == token_id)
        .all()
    )
    assert len(artifacts) == 1, "No new artifact should be created if cache_hit=True."
    assert (
        artifacts[0].cache_hit == True
    ), "Existing artifact should remain cache_hit=True."
