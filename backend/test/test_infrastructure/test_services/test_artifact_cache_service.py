import pytest
from sqlalchemy.orm import Session
from backend.application.services.exceptions import ArtifactNotFoundError
from backend.domain.models import DomainCompiledMultifact
from backend.infrastructure.services.artifact_cache_service import ArtifactCacheService
from backend.infrastructure.entities.ni_token import NIToken
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact
from backend.infrastructure.repositories.artifact_repository import ArtifactRepository
from datetime import datetime, timezone


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
    # First get a real token from the DB
    token = db_session.query(NIToken).first()
    assert token, "Need at least one token in DB"

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
    stored_ent = db_session.query(CompiledMultifact).get(domain_art.id)
    assert stored_ent is not None

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
        cache_hit=False
    )
    db_session.add(new_art)
    db_session.commit()

    repo = ArtifactRepository(db_session)
    # 3) Now update the code
    repo.update_artifact_code(new_art.id, "console.log('updated');", valid=False)

    updated_art = db_session.query(CompiledMultifact).get(new_art.id)
    assert updated_art.code == "console.log('updated');"
    assert updated_art.valid is False, "We changed valid to false."

def test_duplicate_artifact_for_token(db_session: Session):
    # We want to create a new artifact referencing a different token_id,
    # but with the same code from source artifact
    source_ent = CompiledMultifact(
        ni_token_id=1,  # must exist
        language="python",
        framework="flask",
        code="print('hi')",
        valid=True,
        cache_hit=False,
        token_hash="source-hash",
    )
    db_session.add(source_ent)
    db_session.commit()

    # Convert to domain
    from backend.domain.models import DomainCompiledMultifact

    source_dom = source_ent.to_domain_artifact()

    # Suppose we want to duplicate for token_id=2
    new_dom = ArtifactCacheService.duplicate_artifact_for_token(
        2, source_dom, db_session
    )
    # new_dom should have a new ID
    assert new_dom.id != source_dom.id
    assert new_dom.cache_hit == True
    # Check DB
    dupe_ent = db_session.query(CompiledMultifact).get(new_dom.id)
    assert dupe_ent.ni_token_id == 2
    assert dupe_ent.code == "print('hi')"
    assert dupe_ent.cache_hit is True
