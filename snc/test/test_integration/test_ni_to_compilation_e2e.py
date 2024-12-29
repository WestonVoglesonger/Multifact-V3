# File: backend/test/test_integration/test_ni_to_code_compilation_e2e.py

import pytest
from sqlalchemy.orm import Session

# Repositories
from snc.infrastructure.repositories.document_repository import DocumentRepository
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository

from snc.application.services.ni_orchestrator import NIOrchestrator

# Entities
from snc.infrastructure.entities.ni_document import NIDocument

# LLM Model
from snc.infrastructure.llm.model_factory import OpenAIModelType

# The fixture we made
from snc.test.fixtures import ni_orchestrator


@pytest.mark.integration
def test_ni_to_code_compilation_e2e(
    db_session: Session,
    ni_orchestrator: NIOrchestrator,
):
    """
    Comprehensive E2E test verifying we can:
      - Create a doc
      - Update with new NI content
      - Parse/diff/compile
      - End up with valid compiled artifacts
    """

    # 1) Create a brand new doc in DB
    doc_ent = NIDocument(
        content="[Scene:Initial] Just a placeholder", version="test-integration"
    )
    db_session.add(doc_ent)
    db_session.commit()
    doc_id = doc_ent.id

    # 2) We will update it with new content that yields scene+component+function
    new_content = """
    [Scene:MainScene]
    This is main scene content
    [Component:HelloComp]
    A simple HelloComp
    [Function:doStuff]
    This does stuff
    """

    # 3) Call update_ni_and_compile
    ni_orchestrator.update_ni_and_compile(
        ni_id=doc_id,
        new_content=new_content,
        model_type=OpenAIModelType.GPT_4O_MINI,  # or GPT_4O_MINI
        revalidate=True,
    )

    # 4) Check doc updated
    doc_repo = ni_orchestrator.doc_repo
    updated_doc = doc_repo.get_document(doc_id)
    assert updated_doc is not None
    assert updated_doc.content.strip() == new_content.strip()

    # 5) Check tokens in DB
    token_repo = ni_orchestrator.token_repo
    tokens = token_repo.get_all_tokens_for_document(doc_id)
    assert len(tokens) == 3, f"Expected 3 tokens, found {len(tokens)}"

    # 6) Check each token for artifacts
    tokens_with_artifacts = token_repo.get_tokens_with_artifacts(doc_id)
    artifact_map = {}
    for tok_art in tokens_with_artifacts:
        tok, art = tok_art
        if art is not None:
            artifact_map[tok.id] = art

    # All 3 tokens should have an artifact
    assert len(artifact_map) == 3, "Not all tokens got an artifact."

    # 7) Check artifacts are valid
    for t_id, art in artifact_map.items():
        assert art.valid, f"Artifact {art.id} is not valid, code: {art.code}"
        assert art.code.strip(), "Artifact code is empty."

    print(
        "E2E success: Created doc, updated NI, compiled 3 tokens, got valid artifacts!"
    )
