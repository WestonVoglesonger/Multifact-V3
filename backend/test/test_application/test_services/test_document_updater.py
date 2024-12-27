# tests/services/test_document_updater.py

import pytest
from sqlalchemy.orm import Session
from backend.application.services.document_updater import DocumentUpdater
from backend.application.services.token_diff_service import TokenDiffResult
from backend.infrastructure.repositories.document_repository import DocumentRepository
from backend.infrastructure.repositories.token_repository import TokenRepository
from backend.infrastructure.entities.ni_token import NIToken


def compute_hash(content: str) -> str:
    import hashlib

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_document_updater_remove_and_add(db_session: Session):
    """
    Use the doc with [Scene:Updater] inserted by the demo data:
    We'll remove the scene token, add a brand new token, and change the component token.
    """
    doc_repo = DocumentRepository(db_session)
    token_repo = TokenRepository(db_session)
    updater = DocumentUpdater(doc_repo, token_repo)

    # Find doc with [Scene:Updater]
    updater_scene_token = (
        db_session.query(NIToken)
        .filter(NIToken.token_type == "scene", NIToken.scene_name == "Updater")
        .first()
    )
    assert (
        updater_scene_token
    ), "Demo data should have a token with scene_name 'Updater'"
    doc_id = updater_scene_token.ni_document_id

    # Retrieve all tokens for the document
    old_tokens = token_repo.get_tokens_with_artifacts(doc_id)
    assert (
        len(old_tokens) == 2
    ), "Updater doc should have 2 tokens (scene and component)"

    # Correctly unpack the old_tokens
    removed_token, removed_artifact = old_tokens[0]
    changed_token, changed_artifact = old_tokens[1]
    new_token_data = {"type": "function", "content": "New function content."}

    # Build a TokenDiffResult
    diff_result = TokenDiffResult(
        removed=[(removed_token, None)],
        changed=[
            (
                changed_token,
                None,
                {
                    "type": "component",
                    "scene_name": None,
                    "component_name": "UpdaterComp",
                    "content": "Updated UpdaterComp content.",
                },
            )
        ],
        added=[new_token_data],
    )

    # Apply the diff
    updated_tokens = updater.apply_diff(doc_id, "Document updated content", diff_result)

    # Verify that the document content is updated
    updated_doc = doc_repo.get_document(doc_id)
    assert (
        updated_doc.content == "Document updated content"
    ), "Document content should be updated."

    # Verify that the removed token is deleted
    if removed_token.id is None:
        raise ValueError("Token ID cannot be None")
    removed_check = token_repo.get_token_by_id(removed_token.id)
    assert removed_check is None, "Removed token should not exist anymore."

    # Verify that the changed token is updated
    if changed_token.id is None:
        raise ValueError("Token ID cannot be None")
    updated_component = token_repo.get_token_by_id(changed_token.id)
    assert (
        updated_component.content == "Updated UpdaterComp content."
    ), "Component token should be updated."

    # Verify that a new token is added
    assert len(updated_tokens) == 1, "Expect 1 newly added token."
    new_token = updated_tokens[0]
    assert new_token.token_type == "function", "New token should be of type 'function'."
    assert (
        new_token.content == "New function content."
    ), "New token content should match."
    assert new_token.id is not None, "Newly added token should have an ID."
