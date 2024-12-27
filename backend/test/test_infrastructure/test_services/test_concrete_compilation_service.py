# file: backend/new_tests/test_application/test_services/test_concrete_compilation_service.py

import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from backend.infrastructure.services.compilation_service import ConcreteCompilationService
from backend.domain.models import DomainToken
from backend.infrastructure.entities.ni_token import NIToken
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact
from backend.infrastructure.repositories.token_repository import TokenRepository
from backend.test.test_infrastructure.test_llm.mocks import mock_groq_client

def test_compile_token_cache_hit(db_session: Session, mock_groq_client: MagicMock):
    """
    If there's an existing artifact with cache_hit=True for the token, 
    we expect compile_token to return that artifact and not create a new one.
    """
    # 1) Find the token that we inserted with a cached artifact
    #    (We rely on the data from compilation_fake_data_fixture.)
    token_with_cache = db_session.query(NIToken).join(CompiledMultifact).filter(
        CompiledMultifact.cache_hit == True
    ).first()
    assert token_with_cache, "Expected a token with a cache-hit artifact in demo data."

    # 2) Setup services
    compilation_service = ConcreteCompilationService(db_session)
    # mock_llm_client is a fixture that stubs generate_code => not relevant for cache scenario
    # but we pass it anyway
    # e.g. mock_llm_client.generate_code.return_value = "// mocked code"

    # 3) Call compile_token
    artifact_domain = compilation_service.compile_token(token_with_cache.id, mock_groq_client)

    # 4) Check that it returned the existing artifact
    # Because a single artifact with cache_hit=True should exist
    assert artifact_domain.cache_hit is True
    # Ensure no new artifact is in DB
    count_artifacts = db_session.query(CompiledMultifact).filter_by(ni_token_id=token_with_cache.id).count()
    assert count_artifacts == 1, "No new artifact should have been created."

def test_compile_token_no_cache(db_session: Session, mock_groq_client: MagicMock):
    """
    If there's no cache_hit artifact, compile_token should generate code from LLM
    and create a new artifact.
    """
    # 1) Find a token that does *not* have a cache hit
    no_cache_token = db_session.query(NIToken).outerjoin(CompiledMultifact).filter(
        (CompiledMultifact.id == None) | (CompiledMultifact.cache_hit == False)
    ).first()
    assert no_cache_token, "Expected to find a token that does not have a cache artifact."

    # mock LLM generate_code
    mock_groq_client.generate_code.return_value = "// new code from mock"

    compilation_service = ConcreteCompilationService(db_session)
    artifact_domain = compilation_service.compile_token(no_cache_token.id, mock_groq_client)

    assert artifact_domain.cache_hit is False, "New artifact shouldn't be cache_hit."
    assert artifact_domain.code == "// new code from mock"
    # Confirm DB record
    art_in_db = db_session.query(CompiledMultifact).get(artifact_domain.id)
    assert art_in_db, "Artifact should be in DB."
    assert art_in_db.code == "// new code from mock"

def test_compile_token_not_found(db_session: Session, mock_groq_client: MagicMock):
    """
    If the token doesn't exist, compile_token should raise ValueError.
    """
    compilation_service = ConcreteCompilationService(db_session)
    with pytest.raises(ValueError, match="Token with id 999999 not found"):
        compilation_service.compile_token(999999, mock_groq_client)

def test_compile_document(db_session: Session, mock_groq_client: MagicMock):
    """
    Test compile_document with a doc that has 2 tokens. 
    We'll see if it calls compile_token for each token.
    """
    from backend.domain.models import DomainDocument, DomainToken
    # We can build a DomainDocument manually or fetch from DB. 
    # If building from DB, let's just pick the doc with content like [Scene:CompileDoc]
    doc_ent = db_session.query(NIToken).filter(NIToken.token_type=="function").first()
    assert doc_ent, "Need at least one token in DB."

    doc_id = doc_ent.ni_document_id
    # Grab all tokens for that doc
    tokens_in_db = db_session.query(NIToken).filter_by(ni_document_id=doc_id).all()

    # Convert them to DomainTokens
    domain_tokens = []
    for t in tokens_in_db:
        domain_tokens.append(
            DomainToken(
                id=t.id,
                token_uuid=t.token_uuid,
                token_type=t.token_type,
                content=t.content,
                hash=t.hash,
                scene_name=t.scene_name,
                component_name=t.component_name
            )
        )
    domain_doc = DomainDocument(
        doc_id=doc_id,
        content="Some doc content",
        version="vX",
        created_at=tokens_in_db[0].ni_document.created_at,
        updated_at=tokens_in_db[0].ni_document.updated_at,
        tokens=domain_tokens
    )

    # mock LLM
    mock_groq_client.generate_code.return_value = "// doc code"

    compilation_service = ConcreteCompilationService(db_session)
    compiled_ents = compilation_service.compile_document(domain_doc, mock_groq_client)
    # We expect it compiled each token
    assert len(compiled_ents) == len(domain_tokens), "Should have an artifact for each token."

def test_compile_token_with_dependencies(db_session: Session, mock_groq_client: MagicMock):
    """
    If a token has dependencies, compile_token_with_dependencies recursively 
    compiles them first.
    """
    # For this test, we can use the doc that has an S->C->F chain 
    # from the standard "DependencyGraph doc" if you have that in your main fake data.
    # We'll pick 'S' token which depends on 'C', which depends on 'F'.
    # Then call compile_token_with_dependencies(S) and see if F->C->S get compiled in order.
    from backend.infrastructure.services.compilation_service import ConcreteCompilationService
    from backend.infrastructure.repositories.token_repository import TokenRepository

    # Find the token "S" which has dependencies
    token_s = db_session.query(NIToken).filter_by(scene_name="S").one_or_none()
    if not token_s:
        pytest.skip("No scene 'S' found that has dependencies in the demo data.")
    mock_groq_client.generate_code.return_value = "// dep code"

    compilation_service = ConcreteCompilationService(db_session)
    all_arts = compilation_service.compile_token_with_dependencies(token_s.id, mock_groq_client)
    assert len(all_arts) == 3, "Should have compiled S, C, F in total."

