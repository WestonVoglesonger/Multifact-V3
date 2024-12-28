# tests/entities/test_compiled_multifact.py

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.ni_document import NIDocument
from snc.domain.models import DomainCompiledMultifact


def test_compiled_multifact_creation(db_session: Session):
    """
    Test creating a CompiledMultifact by referencing an existing token
    from your demo data.
    """
    # 1) Query a token from demo data
    #    For example, let's grab one of the 'S', 'Updater', or 'RepairDoc' tokens:
    existing_token = db_session.query(NIToken).filter_by(scene_name="S").first()
    assert existing_token, "No token with scene_name='S' in demo data."

    # 2) Now create a new compiled artifact referencing that token’s ID
    artifact = CompiledMultifact(
        ni_token_id=existing_token.id,  # use the real ID from demo data
        language="typescript",
        framework="angular",
        code="console.log('Testing artifact creation');",
        valid=True,
        cache_hit=False,
        token_hash=existing_token.hash,
    )

    # 3) Insert and commit
    db_session.add(artifact)
    db_session.commit()

    # 4) Verify
    assert artifact.id is not None, "Artifact should have an auto-generated ID"
    assert artifact.ni_token_id == existing_token.id
    assert artifact.language == "typescript"
    assert artifact.framework == "angular"
    assert artifact.code == "console.log('Testing artifact creation');"
    assert artifact.valid is True
    assert artifact.cache_hit is False
    assert artifact.token_hash == existing_token.hash


def test_compiled_multifact_to_domain_artifact(db_session: Session):
    """
    Test the to_domain_artifact() method of CompiledMultifact using valid references.
    """

    # 1) Grab an existing document from the demo data
    #    We'll just use the first doc in the table, or you can filter for a specific one
    existing_doc = db_session.query(NIDocument).first()
    assert existing_doc, "No documents found in the database from demo data."
    doc_id = existing_doc.id

    # 2) Create a new token referencing that valid document ID
    token = NIToken(
        ni_document_id=doc_id,  # Must be a valid doc_id from the DB
        token_uuid="artifact-test-uuid2",
        token_type="function",
        token_name="ArtifactTestFunc",
        content="Artifact test content2",
        hash="artifact-test-hash2",
    )
    db_session.add(token)
    db_session.commit()

    # 3) Create a CompiledMultifact referencing the new token
    artifact_ent = CompiledMultifact(
        ni_token_id=token.id,  # references the just-created token
        language="python",
        framework="flask",
        code="print('Hi')",
        valid=False,
        cache_hit=False,
        token_hash="test-hash-xyz",
    )
    db_session.add(artifact_ent)
    db_session.commit()

    # 4) Convert the new DB entity to a domain model
    domain_art = artifact_ent.to_domain_artifact()

    # 5) Assertions
    assert isinstance(domain_art, DomainCompiledMultifact)
    assert domain_art.language == "python"
    assert domain_art.valid is False
    assert domain_art.ni_token_id == token.id
    assert domain_art.cache_hit is False
    assert domain_art.code == "print('Hi')"
    assert domain_art.created_at is not None, "Should have auto-generated created_at"


def test_compiled_multifact_from_domain_artifact(db_session: Session):
    # 1) Grab a token from the fake data
    existing_token = db_session.query(NIToken).filter_by(token_type="function").first()
    assert existing_token, "Expected a function token in the demo data."

    # 2) Build a DomainCompiledMultifact referencing that token's ID
    domain_art = DomainCompiledMultifact(
        artifact_id=0,
        ni_token_id=existing_token.id,  # must match an actual token's ID
        language="go",
        framework="gin",
        code='fmt.Println("Hi")',
        valid=True,
        cache_hit=True,
        created_at=datetime.now(timezone.utc),
    )

    # 3) Convert to entity
    entity_art = CompiledMultifact.to_entity_artifact(domain_art)
    db_session.add(entity_art)
    db_session.commit()

    assert entity_art.id is not None
    assert entity_art.ni_token_id == existing_token.id
    assert entity_art.language == "go"
    assert entity_art.framework == "gin"
    assert entity_art.code == 'fmt.Println("Hi")'
    assert entity_art.valid is True
    assert entity_art.cache_hit is True
