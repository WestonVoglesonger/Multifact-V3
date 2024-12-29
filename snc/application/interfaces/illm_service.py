"""Interface for LLM (Language Model) services."""

from typing import Dict, Any
from abc import ABC, abstractmethod


class ILLMService(ABC):
    """Application-level interface for LLM operations.

    Application services that need to parse documents,
    generate code, or fix code should depend on this interface.
    """

    @abstractmethod
    def parse_document(self, content: str) -> Dict[str, Any]:
        """Parse narrative instructions into structured data.

        Args:
            content: The narrative content to parse

        Returns:
            Dictionary containing the parsed structure
        """
        pass

    @abstractmethod
    def generate_code(
        self,
        token_content: str,
        additional_requirements: str = "",
        code_style: str = "",
    ) -> str:
        """Generate code from a token's narrative description.

        Args:
            token_content: The narrative description to generate code from
            additional_requirements: Optional extra requirements for generation
            code_style: Optional style guide for the generated code

        Returns:
            The generated code as a string
        """
        pass

    @abstractmethod
    def fix_code(self, original_code: str, error_summary: str) -> str:
        """Fix code based on error feedback.

        Args:
            original_code: The code to fix
            error_summary: Description of the errors to fix

        Returns:
            The fixed code as a string
        """
        pass
