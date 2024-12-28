import pytest
from snc.infrastructure.llm.client_factory import ClientFactory
from snc.infrastructure.llm.model_factory import (
    ClientType,
    GroqModelType,
    OpenAIModelType,
)
from snc.infrastructure.llm.groq_llm_client import GroqLLMClient
from snc.infrastructure.llm.openai_llm_client import OpenAILLMClient


def test_client_factory_groq():
    llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)
    assert isinstance(
        llm_client, GroqLLMClient
    ), "Should return a GroqLLMClient instance"


def test_client_factory_openai():
    llm_client = ClientFactory.get_llm_client(OpenAIModelType.GPT_4O)
    assert isinstance(
        llm_client, OpenAILLMClient
    ), "Should return an OpenAILLMClient instance"


def test_client_factory_invalid():
    class FakeModelType:  # or pass something that's not in GroqModelType/OpenAIModelType
        pass

    with pytest.raises(ValueError, match="Unsupported client type"):
        ClientFactory.get_llm_client(FakeModelType())  # type: ignore
