import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.models.ni_document import NIDocumentCreate
from backend.services.ni import NIService
from backend.entities.ni_token import NIToken
from backend.test.services.fixtures import compile_all_tokens_for_doc, mock_llm_side_effect, setup_insert_data_fixture
from typing import Callable

@patch("backend.services.llm.openai_llm_client.OpenAILLMClient._generic_chat_call", side_effect=mock_llm_side_effect)
def test_create_ni_document_single_scene(mock_llm: MagicMock, session_factory: Callable[[], Session]):
    s = session_factory()
    doc_data = NIDocumentCreate(content="[Scene:Intro]\nThis is intro scene.", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, s)
    compile_all_tokens_for_doc(ni_doc.id, s)
    assert ni_doc.id is not None
    assert ni_doc.content == doc_data.content
    assert ni_doc.version == "v1"
    tokens = s.scalars(select(NIToken).where(NIToken.ni_document_id == ni_doc.id)).all()
    assert len(tokens) == 1
    token = tokens[0]
    assert token.scene_name == "Intro"
    assert token.content == "This is intro scene."
    assert len(token.hash) == 64
    s.close()

@patch("backend.services.llm.openai_llm_client.OpenAILLMClient._generic_chat_call", side_effect=mock_llm_side_effect)
def test_create_ni_document_no_scene(mock_llm: MagicMock, session_factory: Callable[[], Session]):
    s = session_factory()
    doc_data = NIDocumentCreate(content="No scene here, just content.", version="v2")
    ni_doc = NIService.create_ni_document(doc_data, s)
    compile_all_tokens_for_doc(ni_doc.id, s)
    tokens = s.scalars(select(NIToken).where(NIToken.ni_document_id == ni_doc.id)).all()
    assert len(tokens) == 1
    token = tokens[0]
    assert token.scene_name == "DefaultScene"
    assert token.content == "No scene here, just content."
    s.close()

@patch("backend.services.llm.openai_llm_client.OpenAILLMClient._generic_chat_call", side_effect=mock_llm_side_effect)
def test_create_ni_document_multiple_scenes(mock_llm: MagicMock, session_factory: Callable[[], Session]):
    s = session_factory()
    doc_data = NIDocumentCreate(content="[Scene:Intro]\nIntro content.\n[Scene:Main]\nMain content here.", version="v3")
    ni_doc = NIService.create_ni_document(doc_data, s)
    compile_all_tokens_for_doc(ni_doc.id, s)
    tokens = s.scalars(select(NIToken).where(NIToken.ni_document_id == ni_doc.id)).all()
    assert len(tokens) == 2
    assert tokens[0].scene_name == "Intro"
    assert tokens[0].content == "Intro content."
    assert tokens[1].scene_name == "Main"
    assert tokens[1].content == "Main content here."
    s.close() 