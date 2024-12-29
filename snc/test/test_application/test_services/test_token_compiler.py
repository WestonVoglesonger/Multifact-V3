# tests/services/test_token_compiler.py

import pytest
from sqlalchemy.orm import Session
from snc.application.services.token_compiler import TokenCompiler
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.services.compilation_service import (
    ConcreteCompilationService,
)
from snc.infrastructure.validation.validation_service import (
    ConcreteValidationService,
)
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.ni_document import NIDocument
from snc.application.services.token_diff_service import TokenDiffService
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from snc.test.test_application.test_services.fixtures import (
    patch_client_factory,
    mock_validation_service_success,
    mock_validation_service_failure,
    mock_llm_client,
)
from snc.infrastructure.llm.client_factory import ClientFactory
from snc.domain.model_types import GroqModelType
from snc.domain.models import DomainToken
from snc.application.interfaces.ivalidation_service import ValidationResult
import uuid


@pytest.fixture(autouse=True)
def cleanup_db(db_session: Session):
    """Clean up the database after each test."""
    yield
    db_session.query(CompiledMultifact).delete()
    db_session.query(NIToken).delete()
    db_session.query(NIDocument).delete()
    db_session.commit()


def test_token_compiler_compile_success(
    db_session: Session,
    patch_client_factory: MagicMock,
    mock_validation_service_success: MagicMock,
):
    """Test that compiling a token with valid code creates an artifact marked as valid."""
    # Create test document and token with unique UUID
    doc = NIDocument(content="Test doc", version="v1")
    db_session.add(doc)
    db_session.commit()

    token_uuid = str(uuid.uuid4())
    token = NIToken(
        ni_document_id=doc.id,
        token_uuid=token_uuid,
        token_type="component",
        token_name="TestComp",
        content="Should compile content.",
        hash="test-hash",
    )
    db_session.add(token)
    db_session.commit()

    # Get DomainToken
    token_repo = TokenRepository(db_session)
    domain_token = token_repo.get_token_by_id(token.id)
    assert domain_token, "Token should be fetched from repository."

    # Setup services
    compilation_service = ConcreteCompilationService(db_session)
    validation_service = ConcreteValidationService(db_session)
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)
    evaluation_service = CodeEvaluationService()

    # Patch validate_artifact on the class
    with patch(
        "snc.infrastructure.validation.validation_service.ConcreteValidationService.validate_artifact"
    ) as mock_validate:
        mock_validate.return_value = ValidationResult(success=True, errors=[])

        compiler = TokenCompiler(
            compilation_service,
            validation_service,
            evaluation_service,
            session=db_session,
        )

        # Call compile_and_validate
        compiler.compile_and_validate([domain_token], llm_client, revalidate=True)

        # Refresh session to see changes from parallel compilation
        db_session.expire_all()

        # Check artifact
        artifact = (
            db_session.query(CompiledMultifact)
            .filter(CompiledMultifact.ni_token_id == token.id)
            .first()
        )
        assert artifact, "Artifact should have been created."
        assert artifact.valid is True, "Artifact should be valid."


def test_token_compiler_compile_fail(
    db_session: Session,
    patch_client_factory: MagicMock,
    mock_validation_service_failure: MagicMock,
):
    """Test that compiling a token with invalid code creates an artifact marked as invalid."""
    # Create test document and token with unique UUID
    doc = NIDocument(content="Test doc", version="v1")
    db_session.add(doc)
    db_session.commit()

    token_uuid = str(uuid.uuid4())
    token = NIToken(
        ni_document_id=doc.id,
        token_uuid=token_uuid,
        token_type="component",
        token_name="TestComp2",
        content="Will fail content.",
        hash="test-hash-2",
    )
    db_session.add(token)
    db_session.commit()

    # Get DomainToken
    token_repo = TokenRepository(db_session)
    domain_token = token_repo.get_token_by_id(token.id)
    assert domain_token, "Token should be fetched from repository."

    # Setup services
    compilation_service = ConcreteCompilationService(db_session)
    validation_service = ConcreteValidationService(db_session)
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)
    evaluation_service = CodeEvaluationService()
    compiler = TokenCompiler(
        compilation_service, validation_service, evaluation_service, session=db_session
    )

    # Call compile_and_validate
    compiler.compile_and_validate([domain_token], llm_client, revalidate=True)

    # Refresh session to see changes from parallel compilation
    db_session.expire_all()

    # Check artifact
    artifact = (
        db_session.query(CompiledMultifact)
        .filter(
            CompiledMultifact.ni_token_id == token.id, CompiledMultifact.valid == False
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
    """Attempting to compile a token with no ID should raise ValueError."""
    # Create a DomainToken in memory (not in DB) with unique UUID
    domain_token = DomainToken(
        id=None,
        token_uuid=str(uuid.uuid4()),
        token_type="scene",
        token_name="NoIdToken",
        content="No ID token",
        hash=TokenDiffService._compute_hash("No ID token"),
    )

    # Setup services
    compilation_service = ConcreteCompilationService(db_session)
    validation_service = ConcreteValidationService(db_session)
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)
    evaluation_service = CodeEvaluationService()
    compiler = TokenCompiler(
        compilation_service, validation_service, evaluation_service, session=db_session
    )

    # Expect ValueError
    with pytest.raises(ValueError, match="Token ID cannot be None"):
        compiler.compile_and_validate([domain_token], llm_client, revalidate=False)


def test_token_compiler_cache_hit(
    db_session: Session,
    patch_client_factory: MagicMock,
    mock_validation_service_success: MagicMock,
):
    """Test that compiling a token with an existing cache_hit=True artifact does not create a new artifact."""
    # Create test document and token with unique UUID
    doc = NIDocument(content="Test doc", version="v1")
    db_session.add(doc)
    db_session.commit()

    token_uuid = str(uuid.uuid4())
    token = NIToken(
        ni_document_id=doc.id,
        token_uuid=token_uuid,
        token_type="component",
        token_name="TestComp3",
        content="Should compile content.",
        hash="test-hash-3",
    )
    db_session.add(token)
    db_session.commit()

    # Create an artifact with cache_hit=True
    existing_artifact = CompiledMultifact(
        ni_token_id=token.id,
        language="typescript",
        framework="angular",
        code="console.log('Hello World');",
        valid=True,
        cache_hit=True,
        token_hash=token.hash,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(existing_artifact)
    db_session.commit()

    # Get DomainToken
    token_repo = TokenRepository(db_session)
    domain_token = token_repo.get_token_by_id(token.id)
    assert domain_token, "Token should be fetched from repository."

    # Setup services
    compilation_service = ConcreteCompilationService(db_session)
    validation_service = ConcreteValidationService(db_session)
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)
    evaluation_service = CodeEvaluationService()
    compiler = TokenCompiler(
        compilation_service, validation_service, evaluation_service, session=db_session
    )

    # Call compile_and_validate with revalidate=False
    compiler.compile_and_validate([domain_token], llm_client, revalidate=False)

    # Refresh session to see changes from parallel compilation
    db_session.expire_all()

    # Ensure no new artifact is created
    artifacts = (
        db_session.query(CompiledMultifact)
        .filter(CompiledMultifact.ni_token_id == token.id)
        .all()
    )
    assert len(artifacts) == 1, "No new artifact should be created if cache_hit=True."
    assert (
        artifacts[0].cache_hit == True
    ), "Existing artifact should remain cache_hit=True."
