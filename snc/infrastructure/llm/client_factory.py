from snc.infrastructure.llm.openai_llm_client import OpenAILLMClient
from snc.infrastructure.llm.groq_llm_client import GroqLLMClient
from snc.domain.models import Model
from snc.domain.model_types import GroqModelType, OpenAIModelType
from snc.domain.client_types import ClientType
from snc.infrastructure.llm.model_factory import ModelFactory


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
