# file: backend/new_tests/test_application/test_services/test_concrete_compilation_service.py

import pytest
from unittest.mock import MagicMock, create_autospec
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import uuid

from snc.infrastructure.services.compilation_service import (
    ConcreteCompilationService,
)
from snc.domain.models import DomainToken, DomainCompiledMultifact, DomainDocument
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.ni_document import NIDocument
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.llm.groq_llm_client import GroqLLMClient
from snc.test.test_infrastructure.test_llm.mocks import mock_groq_client


@pytest.fixture
def mock_llm():
    """Create a mock LLM client for testing."""
    mock = create_autospec(GroqLLMClient)
    mock.generate_code.return_value = "// mocked code"
    return mock


def test_compile_token_cache_hit(db_session: Session, mock_llm: MagicMock):
    """
    If there's an existing artifact with cache_hit=True for the token,
    we expect compile_token to return that artifact and not create a new one.
    """
    # 1) Find a token that has a cached artifact
    token_with_cache = (
        db_session.query(NIToken)
        .join(CompiledMultifact)
        .filter(CompiledMultifact.cache_hit == True)
        .first()
    )
    assert token_with_cache, "Expected a token with a cached artifact in demo data."

    # Clean up any non-cached artifacts for this token
    db_session.query(CompiledMultifact).filter(
        CompiledMultifact.ni_token_id == token_with_cache.id,
        CompiledMultifact.cache_hit == False,
    ).delete()
    db_session.commit()

    # Debug: Print existing artifacts before test
    print("\nBefore test:")
    existing_artifacts = (
        db_session.query(CompiledMultifact).filter_by(ni_token_id=token_with_cache.id).all()
    )
    for art in existing_artifacts:
        print(f"Artifact {art.id}: cache_hit={art.cache_hit}, valid={art.valid}")

    # 2) Setup services
    compilation_service = ConcreteCompilationService(db_session)

    # 3) Call compile_token
    artifact_domain = compilation_service.compile_token(token_with_cache.id, mock_llm)

    # Debug: Print artifacts after test
    print("\nAfter test:")
    final_artifacts = (
        db_session.query(CompiledMultifact).filter_by(ni_token_id=token_with_cache.id).all()
    )
    for art in final_artifacts:
        print(f"Artifact {art.id}: cache_hit={art.cache_hit}, valid={art.valid}")

    # 4) Check that it returned the existing artifact
    # Because a single artifact with cache_hit=True should exist
    assert artifact_domain is not None, "Artifact should be created."
    assert artifact_domain.cache_hit is True
    # Ensure no new artifact is in DB
    count_artifacts = (
        db_session.query(CompiledMultifact).filter_by(ni_token_id=token_with_cache.id).count()
    )
    assert count_artifacts == 1, "No new artifact should have been created."


def test_compile_token_no_cache(db_session: Session, mock_llm: MagicMock):
    """
    If there's no cache_hit artifact, compile_token should generate code from LLM
    and create a new artifact.
    """
    # Create a test document and token
    doc = NIDocument(content="Test doc", version="v1")
    db_session.add(doc)
    db_session.commit()

    token = NIToken(
        ni_document_id=doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="component",
        token_name="TestComp",
        content="Test content",
        hash="test-hash",
    )
    db_session.add(token)
    db_session.commit()

    # mock LLM generate_code
    mock_llm.generate_code.return_value = "// new code from mock"

    compilation_service = ConcreteCompilationService(db_session)
    artifact_domain = compilation_service.compile_token(token.id, mock_llm)

    assert artifact_domain is not None, "Artifact should be created."
    assert artifact_domain.cache_hit is False, "New artifact shouldn't be cache_hit."
    assert artifact_domain.code == "// new code from mock"
    # Confirm DB record
    art_in_db = db_session.query(CompiledMultifact).get(artifact_domain.id)
    assert art_in_db, "Artifact should be in DB."
    assert art_in_db.code == "// new code from mock"


def test_compile_token_not_found(db_session: Session, mock_llm: MagicMock):
    """
    If the token doesn't exist, compile_token should raise ValueError.
    """
    compilation_service = ConcreteCompilationService(db_session)
    with pytest.raises(ValueError, match="Token with id 999999 not found"):
        compilation_service.compile_token(999999, mock_llm)


def test_compile_document(db_session: Session, mock_llm: MagicMock):
    """
    Test compile_document with a doc that has 2 tokens.
    We'll see if it calls compile_token for each token.
    """
    # Create test document and tokens
    doc = NIDocument(content="Test doc", version="v1")
    db_session.add(doc)
    db_session.commit()

    tokens = []
    for i in range(3):
        token = NIToken(
            ni_document_id=doc.id,
            token_uuid=str(uuid.uuid4()),
            token_type="component",
            token_name=f"TestComp{i}",
            content=f"Test content {i}",
            hash=f"test-hash-{i}",
        )
        db_session.add(token)
        tokens.append(token)
    db_session.commit()

    # Convert to domain tokens
    domain_tokens = []
    for t in tokens:
        domain_tokens.append(
            DomainToken(
                id=t.id,
                token_uuid=t.token_uuid,
                token_type=t.token_type,
                token_name=t.token_name,
                content=t.content,
                hash=t.hash,
                scene_name=t.scene_name,
                component_name=t.component_name,
            )
        )

    # Create domain document
    domain_doc = DomainDocument(
        doc_id=doc.id,
        content="Some doc content",
        version="vX",
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        tokens=domain_tokens,
    )

    # mock LLM
    mock_llm.generate_code.return_value = "// doc code"

    compilation_service = ConcreteCompilationService(db_session)
    compiled_ents = compilation_service.compile_document(domain_doc, mock_llm)
    # We expect it compiled each token
    assert len(compiled_ents) == len(domain_tokens), "Should have an artifact for each token."


def test_compile_token_with_dependencies(db_session: Session, mock_llm: MagicMock):
    """
    If a token has dependencies, compile_token_with_dependencies recursively
    compiles them first.
    """
    # Create test document and tokens with dependencies
    doc = NIDocument(content="Test doc", version="v1")
    db_session.add(doc)
    db_session.commit()

    # Create tokens F -> C -> S
    token_f = NIToken(
        ni_document_id=doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="function",
        token_name="F",
        content="Function F",
        hash="hash-f",
        scene_name="S",
        component_name="C",
    )
    db_session.add(token_f)
    db_session.commit()

    token_c = NIToken(
        ni_document_id=doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="component",
        token_name="C",
        content="Component C",
        hash="hash-c",
        scene_name="S",
    )
    db_session.add(token_c)
    db_session.commit()

    token_s = NIToken(
        ni_document_id=doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="scene",
        token_name="S",
        content="Scene S",
        hash="hash-s",
    )
    db_session.add(token_s)
    db_session.commit()

    mock_llm.generate_code.return_value = "// dep code"

    compilation_service = ConcreteCompilationService(db_session)
    all_arts = compilation_service.compile_token_with_dependencies(token_s.id, mock_llm)
    assert len(all_arts) == 3, "Should have compiled S, C, F in total."


def test_compile_simple_code(db_session: Session):
    """Test compiling a simple piece of code."""
    service = ConcreteCompilationService(db_session)
    code = "function test() { return true; }"
    result = service.compile(code)

    assert result.code == code
    assert result.valid is True
    assert result.errors is None
    assert result.cache_hit is False


def test_compile_multifact(db_session: Session):
    """Test compiling a multifact."""
    service = ConcreteCompilationService(db_session)
    multifact = DomainCompiledMultifact(
        artifact_id=1,
        ni_token_id=1,
        language="typescript",
        framework="angular",
        code="export class Test {}",
        valid=True,
        cache_hit=False,
        created_at=datetime.now(),
        score=0.95,
        feedback="Good code",
    )

    result = service.compile(multifact.code)

    assert result.code == multifact.code
    assert result.valid == multifact.valid
    assert result.errors is None
    assert result.cache_hit == multifact.cache_hit
    assert result.score == multifact.score
    assert result.feedback == multifact.feedback
