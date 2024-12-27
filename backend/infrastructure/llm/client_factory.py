from backend.infrastructure.llm.openai_llm_client import OpenAILLMClient
from backend.infrastructure.llm.groq_llm_client import GroqLLMClient
from backend.domain.models import Model
from backend.domain.model_types import GroqModelType, OpenAIModelType
from backend.infrastructure.llm.model_factory import ClientType
from backend.infrastructure.llm.model_factory import ModelFactory
from backend.infrastructure.llm.base_llm_client import BaseLLMClient


class ClientFactory:
    @staticmethod
    def get_llm_client(
        model_type: GroqModelType | OpenAIModelType,
    ) -> GroqLLMClient | OpenAILLMClient:
        if isinstance(model_type, GroqModelType):
            model = ModelFactory.get_model(ClientType.GROQ, model_type)
            return GroqLLMClient(model)
        elif isinstance(model_type, OpenAIModelType):
            model = ModelFactory.get_model(ClientType.OPENAI, model_type)
            return OpenAILLMClient(model)
        else:
            raise ValueError(f"Unsupported client type: {model_type}")
