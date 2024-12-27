# File: test_infrastructure/test_repositories/test_token_repository.py

import pytest
from sqlalchemy.orm import Session
from backend.infrastructure.repositories.token_repository import TokenRepository
from backend.infrastructure.entities.ni_document import NIDocument
from backend.infrastructure.entities.ni_token import NIToken
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact
from backend.domain.models import DomainToken, DomainCompiledMultifact

def test_get_tokens_with_artifacts(db_session: Session):
    """
    Test TokenRepository.get_tokens_with_artifacts(ni_id).
    We rely on the demo data to find a known doc (e.g. 'RepairDoc').
    """
    # Grab the doc with "RepairDoc" in content
    repair_doc = (
        db_session.query(NIDocument)
        .filter(NIDocument.content.like("%[Scene:RepairDoc]%"))
        .first()
    )
    assert repair_doc, "Expected a 'RepairDoc' document in the demo data."

    repo = TokenRepository(db_session)
    result = repo.get_tokens_with_artifacts(repair_doc.id)
    assert len(result) >= 1, "Expected at least one token in the 'RepairDoc'."

    # The doc likely has 1 token for 'RepairDoc' scene. 
    # That token has 2 compiled artifacts in the DB, but .first() picks the first artifact.
    scene_token, maybe_artifact = result[0]
    assert scene_token.token_uuid, "Should have a valid token UUID."
    # We might have an artifact or not, but in your demo data you do have at least 2 artifacts for that token
    assert maybe_artifact, "Expected an artifact for 'RepairDoc' token from the seeded data."


def test_remove_tokens(db_session: Session):
    """
    Test removing tokens and their artifacts.
    We'll create a new doc+token, then remove them.
    """
    # 1) Create a doc
    new_doc = NIDocument(content="[Scene:TempRemove]\n", version="vTest")
    db_session.add(new_doc)
    db_session.commit()

    # 2) Create a token for that doc
    token = NIToken(
        ni_document_id=new_doc.id,
        token_uuid="temp-remove-uuid",
        token_type="scene",
        scene_name="TempRemove",
        content="Temporary token",
        hash="temp-hash",
    )
    db_session.add(token)
    db_session.commit()

    # 3) Create an artifact for that token
    artifact = CompiledMultifact(
        ni_token_id=token.id,
        language="typescript",
        framework="angular",
        code="console.log('temp');",
        valid=True,
        cache_hit=False,
        token_hash="temp-hash",
    )
    db_session.add(artifact)
    db_session.commit()

    # 4) Remove them via TokenRepository
    repo = TokenRepository(db_session)
    domain_tok = repo.get_token_by_id(token.id)
    domain_art = repo.get_artifact(artifact.id)
    assert domain_tok is not None
    assert domain_art is not None

    repo.remove_tokens([domain_tok], [domain_art])

    # 5) Ensure they're gone
    gone_token = db_session.query(NIToken).filter_by(id=token.id).one_or_none()
    gone_art = db_session.query(CompiledMultifact).filter_by(id=artifact.id).one_or_none()
    assert gone_token is None, "Token should be removed"
    assert gone_art is None, "Artifact should be removed"


def test_update_changed_tokens(db_session: Session):
    """
    Test update_changed_tokens. We'll pick a token from the doc with [Scene:Updater].
    """
    doc = (
        db_session.query(NIDocument)
        .filter(NIDocument.content.like("%[Scene:Updater]%"))
        .first()
    )
    assert doc, "Expected an 'Updater' doc in the demo data."

    token_repo = TokenRepository(db_session)
    tokens_with_artifacts = token_repo.get_tokens_with_artifacts(doc.id)
    assert tokens_with_artifacts, "Should have at least one token in that doc."

    old_token, old_art = tokens_with_artifacts[0]
    new_data = {
        "content": "Updated content via test_update_changed_tokens()",
        "type": old_token.token_type,
        "scene_name": old_token.scene_name,
        "component_name": old_token.component_name,
    }
    changed_data = [(old_token, old_art, new_data)]
    token_repo.update_changed_tokens(changed_data)

    if old_token.id is None:
        raise ValueError("Token ID cannot be None")
    updated = token_repo.get_token_by_id(old_token.id)
    assert updated.content == "Updated content via test_update_changed_tokens()"

    # old artifact should be gone if it existed
    if old_art:
        gone_art = (
            db_session.query(CompiledMultifact).filter_by(id=old_art.id).one_or_none()
        )
        assert gone_art is None, "Old artifact should be removed"


def test_add_new_tokens(db_session: Session):
    """
    Test add_new_tokens to an existing doc (e.g. [Scene:Updater]).
    """
    doc = (
        db_session.query(NIDocument)
        .filter(NIDocument.content.like("%[Scene:Updater]%"))
        .first()
    )
    assert doc, "Expected an 'Updater' doc in the demo data."

    token_repo = TokenRepository(db_session)

    new_tokens_data = [
        {
            "type": "function",
            "scene_name": None,
            "component_name": None,
            "content": "func content 1",
        },
        {
            "type": "component",
            "scene_name": None,
            "component_name": "NewComp",
            "content": "NewComp content",
        },
    ]
    created = token_repo.add_new_tokens(doc.id, new_tokens_data)
    assert len(created) == 2, "Should create two new tokens"
    for t in created:
        assert t.id is not None, "New tokens should have an assigned ID"


def test_get_artifact(db_session: Session):
    """
    Retrieve an artifact by ID (valid artifact from 'RepairDoc').
    """
    valid_art = db_session.query(CompiledMultifact).filter_by(valid=True).first()
    assert valid_art, "Expected at least one valid artifact in the DB."

    repo = TokenRepository(db_session)
    domain_art = repo.get_artifact(valid_art.id)
    assert domain_art is not None
    assert domain_art.id == valid_art.id


def test_get_token_by_id(db_session: Session):
    """
    Grab a random token from the DB and see if the repo retrieves it.
    """
    tok_ent = db_session.query(NIToken).first()
    assert tok_ent, "No tokens found in the DB!"
    token_repo = TokenRepository(db_session)

    domain_tok = token_repo.get_token_by_id(tok_ent.id)
    assert domain_tok is not None
    assert domain_tok.id == tok_ent.id
    assert domain_tok.content == tok_ent.content


def test_get_doc_id_for_token_uuid(db_session: Session):
    """
    Confirm we can retrieve a doc ID from a known token's UUID.
    """
    tok_ent = db_session.query(NIToken).first()
    assert tok_ent, "No tokens found in the DB!"
    token_repo = TokenRepository(db_session)

    doc_id = token_repo.get_doc_id_for_token_uuid(tok_ent.token_uuid)
    assert doc_id == tok_ent.ni_document_id


def test_get_all_tokens_for_document(db_session: Session):
    """
    Ensure we retrieve all tokens from the 'Compiler' doc or some doc with multiple tokens.
    """
    comp_doc = (
        db_session.query(NIDocument)
        .filter(NIDocument.content.like("%[Scene:Compiler]%"))
        .first()
    )
    assert comp_doc, "Expected 'Compiler' doc in the DB."

    token_repo = TokenRepository(db_session)
    tokens = token_repo.get_all_tokens_for_document(comp_doc.id)
    assert len(tokens) >= 2, "'Compiler' doc should have at least 2 tokens (ShouldCompile, WillFail)."
