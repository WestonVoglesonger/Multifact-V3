import pytest
from sqlalchemy.orm import Session
from .demo_data import insert_demo_data
from backend.services.ni import NIService
from backend.models.ni_document import NIDocumentCreate
from backend.entities.ni_token import NIToken
from backend.services.compilation import CompilationService
from backend.services.llm.openai_llm_client import OpenAILLMClient
from backend.services.llm.groq_llm_client import GroqLLMClient
from backend.services.llm.model_factory import OpenAIModelType, GroqModelType
from sqlalchemy import select
from backend.services.validation.validation_service import ValidationService
from unittest.mock import patch
from backend.services.llm.base_llm_client import BaseLLMClient
from backend.services.llm.openai_llm_client import OpenAILLMClient
import os
MOCK_GENERATED_CODE = """\
import { Component } from '@angular/core';

@Component({
  selector: 'app-test',
  template: `<div>Test Component</div>`
})
export class TestComponent {}
"""

def mock_llm_side_effect(
    system_message: dict,
    user_message: dict,
    model: str = "gpt-4o-mini",
    temperature: float = 0,
    max_tokens: int = 3000,
) -> str:
    prompt = user_message["content"]
    # Check if this is a parsing call
    is_parsing = "Now return the JSON." in prompt or "Return the JSON." in prompt

    if is_parsing:
        # Return JSON for parsing scenarios
        if "[Scene:Intro]" in prompt and "This is intro scene." in prompt:
            return '{"scenes":[{"name":"Intro","narrative":"This is intro scene.","components":[]}]}' 

        if "No scene here" in prompt:
            return '{"scenes":[{"name":"DefaultScene","narrative":"No scene here, just content.","components":[]}]}' 

        if "[Scene:Intro]" in prompt and "[Scene:Main]" in prompt:
            return '{"scenes":[{"name":"Intro","narrative":"Intro content.","components":[]},{"name":"Main","narrative":"Main content here.","components":[]}]}' 

        if (
            "[Scene:Main]" in prompt
            and "[Component:MyComponent]" in prompt
            and "[Function:sendEmail]" in prompt
        ):
            return '{"scenes":[{"name":"Main","narrative":"","components":[{"name":"MyComponent","narrative":"Some component text\\nHere goes function body.\\nEnd of function.","functions":[]}]}]}'

        if "Just some text without any tags." in prompt:
            return '{"scenes":[{"name":"DefaultScene","narrative":"Just some text without any tags.","components":[]}]}' 

        if "[Scene:CacheTest]" in prompt and "This is a test." in prompt:
            return '{"scenes":[{"name":"CacheTest","narrative":"This is a test.","components":[]}]}' 

        if (
            "[Scene:A]" in prompt
            and "[Component:X]" in prompt
            and "[Scene:B]" in prompt
        ):
            if "X comp updated" in prompt:
                return '{"scenes":[{"name":"A","narrative":"AAA","components":[{"name":"X","narrative":"X comp updated","functions":[]}]},{"name":"B","narrative":"BBB","components":[{"name":"Y","narrative":"Y comp","functions":[]}]}]}'
            else:
                return '{"scenes":[{"name":"A","narrative":"AAA","components":[{"name":"X","narrative":"X comp","functions":[]}]},{"name":"B","narrative":"BBB","components":[{"name":"Y","narrative":"Y comp","functions":[]}]}]}'

        if "[Scene:CCache]" in prompt:
            return '{"scenes":[{"name":"CCache","narrative":"Hello same content","components":[]}]}' 

        if "[Scene:Long]" in prompt:
            return '{"scenes":[{"name":"Long","narrative":"Line 0\\nLine 1\\n...","components":[]}]}' 

        # Default fallback
        return '{"scenes":[{"name":"DefaultScene","narrative":"","components":[]}]}' 
    else:
        # This is a code generation call
        return MOCK_GENERATED_CODE

@pytest.fixture(autouse=True)
def setup_insert_data_fixture(db_session: Session, llm_client: BaseLLMClient):
    insert_demo_data(db_session, llm_client)
    db_session.commit()
    yield

def compile_all_tokens_for_doc(ni_doc_id: int, session: Session, llm_client: BaseLLMClient):
    tokens = session.query(NIToken).filter_by(ni_document_id=ni_doc_id).all()
    for t in tokens:
        CompilationService.compile_token(t.id, session, llm_client)

@pytest.fixture
def initial_ni(db_session: Session, llm_client: BaseLLMClient):
    doc_data = NIDocumentCreate(
        content=(
            "[Scene:Intro]\nIntro line\n[Component:Greeting]\ngreet user\n\n"
            "[Scene:Main]\nmain line\n[Component:Dashboard]\nshow data"
        ),
        version="v1",
    )
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    tokens = db_session.scalars(
        select(NIToken).where(NIToken.ni_document_id == ni_doc.id)
    ).all()
    for t in tokens:
        CompilationService.compile_token(t.id, db_session, llm_client)
    return ni_doc

@pytest.fixture
def ni_with_component_and_method(db_session: Session, llm_client: BaseLLMClient):
    doc_data = NIDocumentCreate(
        content="[Scene:Spec]\nCreate a component named MyComponent with a method sendEmail()",
        version="v1",
    )
    ni_doc = NIService.create_ni_document(doc_data, db_session, llm_client)
    compile_all_tokens_for_doc(ni_doc.id, db_session, llm_client)
    return ni_doc

@pytest.fixture
def ni_with_component_and_multiple_methods(db_session: Session, llm_client: BaseLLMClient):
    doc_data = NIDocumentCreate(
        content="[Scene:Spec]\nCreate a component named MyComponent with methods sendEmail and handleClick",
        version="v1",
    )
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    tokens = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    for t in tokens:
        CompilationService.compile_token(t.id, db_session, llm_client)
    return ni_doc

def insert_artifact(db_session: Session, token: NIToken, code: str, valid: bool = True):
    from backend.entities.compiled_multifact import CompiledMultifact

    artifact = CompiledMultifact(
        ni_token_id=token.id,
        language="typescript",
        framework="angular",
        code=code,
        valid=valid,
        cache_hit=False,
    )
    db_session.add(artifact)
    db_session.commit()
    db_session.refresh(artifact)
    return artifact

def insert_custom_artifact(
    db_session: Session, token: NIToken, code: str, valid: bool = True
):
    return insert_artifact(db_session, token, code, valid)

@pytest.fixture(autouse=True)
def mock_subprocess_run():
    with patch("backend.services.validation.validation_service.run") as mocked_run:
        mocked_run.return_value.stdout = ""
        mocked_run.return_value.stderr = ""
        mocked_run.return_value.returncode = 0
        yield mocked_run


@pytest.fixture
def llm_client():
    """
    Fixture to instantiate the LLM client based on environment variables.
    LLM_CLIENT_TYPE: "openai" or "groq"
    LLM_MODEL_TYPE: a string like "gpt-4o", "gpt-4o-mini", "o1", etc for OpenAI
                    or "gemma2-9b-it", "llama3-8b-8192" etc for Groq.
    """
    llm_client_type = os.environ.get("LLM_CLIENT_TYPE", "openai")
    llm_model_type = os.environ.get("LLM_MODEL_TYPE", "gpt-4o-mini")

    if llm_client_type == "openai":
        # Convert model_type_str to OpenAIModelType
        openai_map = {
            "gpt-4o": OpenAIModelType.GPT_4O,
            "gpt-4o-mini": OpenAIModelType.GPT_4O_MINI,
            "o1": OpenAIModelType.O1,
            "o1-mini": OpenAIModelType.O1_MINI
        }
        if llm_model_type not in openai_map:
            raise ValueError(f"Unknown OpenAI model: {llm_model_type}")
        mtype = openai_map[llm_model_type]
        return OpenAILLMClient(mtype)

    elif llm_client_type == "groq":
        groq_map = {
            "gemma2-9b-it": GroqModelType.GEMMA2_9B_IT,
            "gemma-7b-it": GroqModelType.GEMMA_7B_IT,
            "llama-3.3-70b-versatile": GroqModelType.LLAMA_3_3_70B_VERSATILE,
            "llama-3.1-8b-instant": GroqModelType.LLAMA_3_1_8B_INSTANT,
            "llama-guard-3-8b": GroqModelType.LLAMA_GUARD_3_8B,
            "llama3-70b-8192": GroqModelType.LLAMA3_70B_8192,
            "llama3-8b-8192": GroqModelType.LLAMA3_8B_8192,
            "mixtral-8x7b-32768": GroqModelType.MIXTRAL_8X7B_32768
        }
        if llm_model_type not in groq_map:
            raise ValueError(f"Unknown Groq model: {llm_model_type}")
        gmtype = groq_map[llm_model_type]
        return GroqLLMClient(gmtype)

    else:
        raise ValueError(f"Unknown client type: {llm_client_type}")
