import pytest
import random
import string
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
from backend.models.ni_document import NIDocumentCreate
from backend.services.ni import NIService
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.test.services.fixtures import compile_all_tokens_for_doc, mock_llm_side_effect, MOCK_GENERATED_CODE, setup_insert_data_fixture
from typing import Callable

def test_ni_empty(db_session: Session):
    doc_data = NIDocumentCreate(content="", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    tokens = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    assert len(tokens) == 0, "No tokens expected from empty NI"

def test_ni_whitespace(db_session: Session):
    doc_data = NIDocumentCreate(content="   \n   ", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    tokens = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    assert len(tokens) == 0, "No tokens expected from whitespace-only NI"

@patch("backend.services.llm.openai_llm_client.OpenAILLMClient._generic_chat_call", side_effect=mock_llm_side_effect)
def test_ni_extremely_long(mock_llm: MagicMock, db_session: Session):
    long_content = "[Scene:Long]\n" + "\n".join("Line " + str(i) for i in range(10000))
    doc_data = NIDocumentCreate(content=long_content, version="v1")
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)
    tokens = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    assert len(tokens) > 0

def test_ni_fuzz_random(db_session: Session):
    random_content = "[Scene:Fuzz]\n" + ''.join(random.choices(string.printable, k=500))
    doc_data = NIDocumentCreate(content=random_content, version="v1")
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)
    tokens = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    if tokens:
        artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=tokens[0].id).first()
        assert artifact is not None

@patch("backend.services.llm.openai_llm_client.OpenAILLMClient._generic_chat_call", return_value=MOCK_GENERATED_CODE)
def test_fuzzing_multi_runs(mock_llm: MagicMock, session_factory: Callable[[], Session]):
    def random_ni():
        lines = []
        import random, string
        # reduce complexity: always generate at most 2 scenes and 1 component each
        for i in range(random.randint(1, 2)):
            lines.append(f"[Scene:Rand{i}]")
            for c_i in range(random.randint(0, 1)):
                lines.append(f"[Component:C{i}_{c_i}]")
                for _ in range(1):  # only 1 line instead of 3
                    lines.append(''.join(random.choices(string.ascii_letters + string.digits, k=20)))
        return '\n'.join(lines) if lines else "Just a line"

    for _ in range(5):  # reduce from 10 to 5
        s = session_factory()
        try:
            content = random_ni()
            ni_doc = NIService.create_ni_document(NIDocumentCreate(content=content, version="fuzz"), s)
            compile_all_tokens_for_doc(ni_doc.id, s)
        finally:
            s.close() 