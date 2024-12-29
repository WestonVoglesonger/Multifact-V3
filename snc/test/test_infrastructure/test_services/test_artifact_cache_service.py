import pytest
from sqlalchemy.orm import Session
from snc.application.services.exceptions import ArtifactNotFoundError
from snc.domain.models import DomainCompiledMultifact
from snc.infrastructure.services.artifact_cache_service import ArtifactCacheService
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository
from datetime import datetime, timezone
from snc.infrastructure.entities.ni_document import NIDocument


def test_get_artifact_by_hash_not_found(db_session: Session):
    result = ArtifactCacheService.get_artifact_by_hash("some-random-hash", db_session)
    assert result is None, "Should return None if not found"


def test_get_artifact_by_hash_found(db_session: Session):
    # Grab an existing artifact from your data, check its token_hash
    existing_art = db_session.query(CompiledMultifact).first()
    if not existing_art or not existing_art.token_hash:
        pytest.skip("Need an artifact with a token_hash in demo data.")
    # Now call get_artifact_by_hash
    domain_art = ArtifactCacheService.get_artifact_by_hash(
        existing_art.token_hash, db_session
    )
    assert domain_art is not None
    assert domain_art.id == existing_art.id


def test_store_artifact_new(db_session: Session):
    # First create a token
    doc = NIDocument(content="test doc", version="v1")
    db_session.add(doc)
    db_session.commit()

    token = NIToken(
        ni_document_id=doc.id,
        token_uuid="test-uuid",
        token_type="component",
        token_name="TestComp",
        content="test content",
        hash="test-hash",
    )
    db_session.add(token)
    db_session.commit()

    # Create domain artifact with valid token_id
    domain_art = DomainCompiledMultifact(
        artifact_id=0,  # indicates new
        ni_token_id=token.id,  # use actual token ID
        language="go",
        framework="gin",
        code='fmt.Println("Hello")',
        valid=True,
        cache_hit=False,
        created_at=datetime.now(timezone.utc),
    )
    token_hash = "hash-store-test"
    ArtifactCacheService.store_artifact(token_hash, domain_art, db_session)
    assert domain_art.id is not None

    # Check DB
    stored_ent = db_session.get(CompiledMultifact, domain_art.id)
    assert stored_ent is not None
    assert stored_ent.code == 'fmt.Println("Hello")'
    assert stored_ent.token_hash == token_hash


def test_update_artifact_code(db_session: Session):
    """
    Test updating artifact code and validity. We'll pick a real token from DB for the foreign key.
    """
    # 1) Find a real token from the DB
    some_token = db_session.query(NIToken).first()
    assert some_token, "We need at least one existing token from the seeded data."

    # 2) Create a new artifact referencing that token
    new_art = CompiledMultifact(
        ni_token_id=some_token.id,
        language="typescript",
        framework="angular",
        code="console.log('original');",
        valid=True,
        cache_hit=False,
    )
    db_session.add(new_art)
    db_session.commit()

    repo = ArtifactRepository(db_session)
    # 3) Now update the code
    repo.update_artifact_code(new_art.id, "console.log('updated');", valid=False)

    updated_art = db_session.query(CompiledMultifact).get(new_art.id)
    assert updated_art is not None, "Updated artifact should exist"
    assert updated_art.code == "console.log('updated');"
    assert updated_art.valid is False, "We changed valid to false."


def test_duplicate_artifact_for_token(db_session: Session):
    # First create a document and token
    doc = NIDocument(content="test doc", version="v1")
    db_session.add(doc)
    db_session.commit()

    token = NIToken(
        ni_document_id=doc.id,
        token_uuid="test-uuid",
        token_type="component",
        token_name="TestComp",
        content="test content",
        hash="test-hash",
    )
    db_session.add(token)
    db_session.commit()

    # Create source artifact
    source_ent = CompiledMultifact(
        ni_token_id=token.id,
        language="python",
        framework="flask",
        code="print('hi')",
        valid=True,
        cache_hit=False,
        token_hash="source-hash",
    )
    db_session.add(source_ent)
    db_session.commit()

    # Create another token to duplicate to
    token2 = NIToken(
        ni_document_id=doc.id,
        token_uuid="test-uuid-2",
        token_type="component",
        token_name="TestComp2",
        content="test content 2",
        hash="test-hash-2",
    )
    db_session.add(token2)
    db_session.commit()

    # Convert to domain model
    source_domain = source_ent.to_domain_artifact()

    # Duplicate for new token
    new_domain = ArtifactCacheService.duplicate_artifact_for_token(
        token2.id, source_domain, db_session
    )

    # Verify duplication
    assert new_domain.id != source_domain.id
    assert new_domain.ni_token_id == token2.id
    assert new_domain.code == source_domain.code
    assert new_domain.cache_hit is True
