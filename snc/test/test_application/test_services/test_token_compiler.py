# tests/services/test_token_compiler.py

import pytest
from sqlalchemy.orm import Session, sessionmaker
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
from snc.database import engine
import uuid


@pytest.fixture(autouse=True)
def cleanup_db(db_session: Session):
    """Clean up the database after each test."""
    yield
    db_session.query(CompiledMultifact).delete()
    db_session.query(NIToken).delete()
    db_session.query(NIDocument).delete()
    db_session.commit()


@pytest.fixture
def session_factory():
    """Create a session factory for tests."""
    return sessionmaker(bind=engine)


@pytest.fixture
def compilation_service(db_session: Session) -> ConcreteCompilationService:
    """Create a compilation service for testing."""
    return ConcreteCompilationService(db_session)


@pytest.fixture
def validation_service(db_session: Session) -> ConcreteValidationService:
    """Create a validation service for testing."""
    return ConcreteValidationService(db_session)


@pytest.fixture
def token_repo(db_session: Session) -> TokenRepository:
    """Create a token repository for testing."""
    return TokenRepository(db_session)


@pytest.fixture
def token_compiler(
    compilation_service: ConcreteCompilationService,
    validation_service: ConcreteValidationService,
    token_repo: TokenRepository,
    session_factory: sessionmaker,
) -> TokenCompiler:
    """Create a TokenCompiler instance for testing."""
    return TokenCompiler(
        compilation_service=compilation_service,
        validation_service=validation_service,
        session_factory=session_factory,
        token_repository=token_repo,
    )


def test_token_compiler_compile_success(
    db_session: Session,
    patch_client_factory: MagicMock,
    mock_validation_service_success: MagicMock,
    token_compiler: TokenCompiler,
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

    # Get LLM client
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)

    # Patch validate_artifact on the class
    with patch(
        "snc.infrastructure.validation.validation_service.ConcreteValidationService.validate_artifact"
    ) as mock_validate:
        mock_validate.return_value = ValidationResult(success=True, errors=[])

        # Call compile_and_validate
        token_compiler.compile_and_validate([domain_token], llm_client, revalidate=True)

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
    token_compiler: TokenCompiler,
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

    # Get LLM client
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)

    # Call compile_and_validate
    token_compiler.compile_and_validate([domain_token], llm_client, revalidate=True)

    # Refresh session to see changes from parallel compilation
    db_session.expire_all()

    # Check artifact
    artifact = (
        db_session.query(CompiledMultifact)
        .filter(CompiledMultifact.ni_token_id == token.id)
        .first()
    )
    assert artifact, "Artifact should have been created."
    assert artifact.valid is False, "Artifact should be invalid."


def test_token_compiler_no_id_raises_error(
    db_session: Session,
    patch_client_factory: MagicMock,
    token_compiler: TokenCompiler,
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

    # Get LLM client
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)

    # Call compile_and_validate should raise ValueError
    with pytest.raises(ValueError, match="Token ID cannot be None"):
        token_compiler.compile_and_validate([domain_token], llm_client, revalidate=True)


def test_token_compiler_cache_hit(
    db_session: Session,
    patch_client_factory: MagicMock,
    mock_validation_service_success: MagicMock,
    token_compiler: TokenCompiler,
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

    # Get LLM client
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)

    # Call compile_and_validate
    token_compiler.compile_and_validate([domain_token], llm_client, revalidate=True)

    # Refresh session to see changes from parallel compilation
    db_session.expire_all()

    # Check that no new artifact was created
    artifacts = (
        db_session.query(CompiledMultifact).filter(CompiledMultifact.ni_token_id == token.id).all()
    )
    assert len(artifacts) == 1, "Should not have created a new artifact."
    assert artifacts[0].id == existing_artifact.id, "Should have reused existing artifact."
