import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from backend.models.ni_document import NIDocumentCreate
from backend.services.ni import NIService
from backend.services.compilation import CompilationService
from backend.test.services.fixtures import compile_all_tokens_for_doc, mock_llm_side_effect, setup_insert_data_fixture
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact

MOCK_GENERATED_CODE = """\
import { Component } from '@angular/core';

@Component({
  selector: 'app-test',
  template: `<div>Test Component</div>`
})
export class TestComponent {}
"""

@patch("backend.services.llm.openai_llm_client.OpenAILLMClient._generic_chat_call", side_effect=mock_llm_side_effect)
def test_compile_token_new(mock_llm: MagicMock, db_session: Session):
    doc_data = NIDocumentCreate(content="[Scene:Intro]\nThis is intro scene.", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)

    token = db_session.get(NIToken, ni_doc.id)
    assert token is not None, "Token should have been created."

    artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()
    assert artifact is not None, "Artifact should be created after compilation."
    assert len(artifact.code.strip()) > 0, "Artifact code should not be empty."
    assert "@component" in artifact.code.lower(), "Artifact code should contain @component."

def test_compile_token_non_existent(db_session: Session):
    with pytest.raises(ValueError):
        CompilationService.compile_token(9999, db_session)

@patch("backend.services.llm.openai_llm_client.OpenAILLMClient._generic_chat_call", side_effect=mock_llm_side_effect)
def test_compile_token_cache(mock_llm: MagicMock, db_session: Session):
    doc_data = NIDocumentCreate(content="Just some content no scenes", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)

    from backend.entities.ni_token import NIToken
    from backend.entities.compiled_multifact import CompiledMultifact

    token = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).first()
    artifact_1 = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()
    assert artifact_1 is not None
    assert artifact_1.cache_hit == False

    # Compile again - should hit cache now
    CompilationService.compile_token(token.id, db_session) 
    artifact_2 = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()
    assert artifact_2 is not None
    assert artifact_2.id == artifact_1.id
    assert artifact_2.cache_hit is True