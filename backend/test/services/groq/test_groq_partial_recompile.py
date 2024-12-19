import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from backend.models.ni_document import NIDocumentCreate
from backend.services.ni import NIService
from backend.services.user_intervention import UserInterventionService
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.test.services.fixtures import compile_all_tokens_for_doc, mock_llm_side_effect, setup_insert_data_fixture

@patch("backend.services.llm.groq_llm_client.GroqLLMClient._generic_chat_call", side_effect=mock_llm_side_effect)
def test_partial_recompile_only_changed_tokens(mock_llm: MagicMock, db_session: Session):
    doc_data = NIDocumentCreate(
        content="[Scene:A]\nAAA\n[Component:X]\nX comp\n[Scene:B]\nBBB\n[Component:Y]\nY comp",
        version="v1"
    )
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)

    tokens = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    old_map = {}
    for t in tokens:
        artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=t.id).first()
        old_map[UserInterventionService.make_key_from_db_token(t)] = artifact

    original_content = ni_doc.content
    modified_content = original_content.replace("X comp","X comp updated")
    UserInterventionService.update_ni_and_recompile(ni_doc.id, modified_content, db_session)

    new_tokens = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    new_map = {}
    for t in new_tokens:
        artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=t.id).first()
        key = UserInterventionService.make_key_from_db_token(t)
        new_map[key] = artifact

    changed_key = ("component", "X")
    old_art = old_map[changed_key]
    new_art = new_map[changed_key]
    assert new_art is not None
    assert old_art is not None
    assert new_art.id != old_art.id
    assert new_art.cache_hit == False

    unchanged_keys = set(old_map.keys()) - {changed_key}
    for k in unchanged_keys:
        assert old_map[k] is not None
        assert new_map[k] is not None
        assert old_map[k].id == new_map[k].id