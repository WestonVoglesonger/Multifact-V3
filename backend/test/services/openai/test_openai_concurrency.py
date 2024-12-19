import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
from backend.models.ni_document import NIDocumentCreate
from backend.services.ni import NIService
from backend.services.compilation import CompilationService
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.entities.ni_document import NIDocument
from backend.test.services.fixtures import MOCK_GENERATED_CODE, compile_all_tokens_for_doc, setup_insert_data_fixture
from typing import Callable

def compile_all_tokens_for_doc(ni_doc_id: int, session: Session):
    tokens = session.query(NIToken).filter_by(ni_document_id=ni_doc_id).all()
    for t in tokens:
        CompilationService.compile_token(t.id, session)

def mock_llm_side_effect(system_message: dict, user_message: dict, model: str = "gpt-4", temperature: float = 0, max_tokens: int = 3000) -> str:
    prompt = user_message["content"]

    # Check if this is a parsing call (must contain "Now return the JSON.")
    is_parsing = "Now return the JSON." in prompt or "Return the JSON." in prompt

    if is_parsing:
        # Define responses based on prompt content
        if "[Scene:Intro]" in prompt and "This is intro scene." in prompt:
            return '{"scenes":[{"name":"Intro","narrative":"This is intro scene.","components":[]}]}'

        if "No scene here" in prompt:
            return '{"scenes":[{"name":"DefaultScene","narrative":"No scene here, just content.","components":[]}]}'

        if "[Scene:Intro]" in prompt and "[Scene:Main]" in prompt:
            return '{"scenes":[{"name":"Intro","narrative":"Intro content.","components":[]},{"name":"Main","narrative":"Main content here.","components":[]}]}' 

        if "[Scene:Main]" in prompt and "[Component:MyComponent]" in prompt and "[Function:sendEmail]" in prompt:
            return '{"scenes":[{"name":"Main","narrative":"","components":[{"name":"MyComponent","narrative":"Some component text\nHere goes function body.\nEnd of function.","functions":[]}]}]}'

        if "Just some text without any tags." in prompt:
            return '{"scenes":[{"name":"DefaultScene","narrative":"Just some text without any tags.","components":[]}]}'

        if "[Scene:CacheTest]" in prompt and "This is a test." in prompt:
            return '{"scenes":[{"name":"CacheTest","narrative":"This is a test.","components":[]}]}'

        if "[Scene:Long]" in prompt:
            return '{"scenes":[{"name":"Long","narrative":"Line 0\nLine 1\n...","components":[]}]}'

        # Default fallback if no conditions matched:
        return '{"scenes":[{"name":"DefaultScene","narrative":"","components":[]}]}'

    else:
        # This is a code generation call
        return MOCK_GENERATED_CODE

@patch("backend.services.llm.openai_llm_client.OpenAILLMClient._generic_chat_call", side_effect=mock_llm_side_effect)
def test_concurrent_same_tokens_cache(mock_llm: MagicMock, session_factory: Callable[[], Session]):
    def create_same_doc():
        s = session_factory()
        try:
            doc_data = NIDocumentCreate(content="[Scene:CCache]\nHello same content", version="v1")
            ni_doc = NIService.create_ni_document(doc_data, s)
            compile_all_tokens_for_doc(ni_doc.id, s)
        finally:
            s.close()

    # Run multiple threads
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_same_doc) for _ in range(5)]
        for f in futures:
            f.result()  # ensure no exception

    s = session_factory()
    try:
        docs = s.query(NIDocument).filter(NIDocument.content.like("%[Scene:CCache]%")).all()
        all_token_ids = [t.id for d in docs for t in s.query(NIToken).filter_by(nid_document_id=d.id).all()]
        artifacts = s.query(CompiledMultifact).filter(CompiledMultifact.ni_token_id.in_(all_token_ids)).all()

        codes = set(a.code for a in artifacts)
        # Now we should have the same code artifact since same content leads to same hash and cache hit.
        assert len(codes) == 1, f"All identical docs should produce the same code artifact, found {len(codes)} distinct."
    finally:
        s.close() 