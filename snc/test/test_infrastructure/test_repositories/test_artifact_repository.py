# File: test_infrastructure/test_repositories/test_artifact_repository.py

import pytest
from sqlalchemy.orm import Session
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.ni_document import NIDocument
from snc.domain.models import DomainCompiledMultifact


def test_get_artifact_by_id(db_session: Session):
    """
    Retrieve an existing artifact from the demo data (e.g. valid artifact from 'RepairDoc').
    """
    valid_art = db_session.query(CompiledMultifact).filter_by(valid=True).first()
    assert valid_art, "Expected at least one valid artifact."

    repo = ArtifactRepository(db_session)
    domain_art = repo.get_artifact_by_id(valid_art.id)
    assert domain_art is not None
    assert domain_art.id == valid_art.id


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
    assert updated_art.code == "console.log('updated');"
    assert updated_art.valid is False, "We changed valid to false."
