"""
Base interface for LLM clients.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json

class BaseLLMClient(ABC):
    def __init__(self):
        self.last_usage: Optional[Dict[str, int]] = None
        self.last_cost: Optional[float] = None

    @abstractmethod
    def parse_document(self, ni_content: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def generate_code(self, token_content: str, additional_requirements: str = "", code_style: str = "") -> str:
        pass

    @abstractmethod
    def fix_code(self, original_code: str, error_summary: str) -> str:
        pass

    def _attempt_json_parse(self, text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
