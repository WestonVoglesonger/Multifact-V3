from snc.application.interfaces.illm_service import ILLMService
from snc.infrastructure.llm.client_factory import ClientFactory
from typing import Dict, Any
from snc.domain.model_types import GroqModelType, OpenAIModelType


class ConcreteLLMService(ILLMService):
    """
    This class implements ILLMService and uses ClientFactory to get an ILLMClient implementation.
    It doesn't tie the application layer to a specific LLM implementation.
    """

    def __init__(self, model_type: GroqModelType | OpenAIModelType):
        # model_type could be passed in from configuration
        self.llm_client = ClientFactory.get_llm_client(model_type)

    def parse_document(self, content: str) -> Dict[str, Any]:
        return self.llm_client.parse_document(content)

    def generate_code(
        self,
        token_content: str,
        additional_requirements: str = "",
        code_style: str = "",
    ) -> str:
        return self.llm_client.generate_code(token_content, additional_requirements, code_style)

    def fix_code(self, original_code: str, error_summary: str) -> str:
        return self.llm_client.fix_code(original_code, error_summary)
