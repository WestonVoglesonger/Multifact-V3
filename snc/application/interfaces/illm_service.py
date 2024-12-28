from typing import Dict, Any
from abc import ABC, abstractmethod


class ILLMService(ABC):
    """
    Application-level interface for LLM operations.
    Application services that need to parse documents,
    generate code, or fix code should depend on this interface.
    """

    @abstractmethod
    def parse_document(self, content: str) -> Dict[str, Any]:
        """
        Parse the given narrative instructions and return a structured dict
        """

    @abstractmethod
    def generate_code(
        self,
        token_content: str,
        additional_requirements: str = "",
        code_style: str = "",
    ) -> str:
        """
        Generate code from a token's narrative description.
        """

    @abstractmethod
    def fix_code(self, original_code: str, error_summary: str) -> str:
        """
        Given original code and an error summary, produce a corrected version of the code.
        """
