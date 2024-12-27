from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
from backend.domain.models import Model


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients. In the infrastructure layer.
    """

    def __init__(self, model: Model):
        self.last_usage: Optional[Dict[str, int]] = None
        self.last_cost: Optional[float] = None
        self.model: Model = model

    @abstractmethod
    def parse_document(self, ni_content: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def generate_code(
        self,
        token_content: str,
        additional_requirements: str = "",
        code_style: str = "",
    ) -> str:
        pass

    @abstractmethod
    def fix_code(self, original_code: str, error_summary: str) -> str:
        pass

    def _attempt_json_parse(self, text: str) -> Optional[dict]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    @abstractmethod
    def _generic_chat_call(
        self,
        system_message: Dict[str, Any],
        user_message: Dict[str, Any],
        model_name: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        pass
