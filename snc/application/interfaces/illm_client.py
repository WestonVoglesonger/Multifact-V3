"""Interface for Language Model client implementations."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class ILLMClient(ABC):
    """Interface for LLM clients for code generation and evaluation."""

    @abstractmethod
    def generate_code(self, prompt: str, **kwargs: Any) -> str:
        """Generate code based on a prompt.

        Args:
            prompt: The prompt describing the code to generate
            **kwargs: Additional arguments for the LLM

        Returns:
            Generated code as a string
        """
        pass

    @abstractmethod
    def evaluate_code(self, code: str, requirements: str) -> Dict[str, Any]:
        """Evaluate code against requirements.

        Args:
            code: The code to evaluate
            requirements: Requirements to evaluate against

        Returns:
            Dictionary containing evaluation results
        """
        pass

    @abstractmethod
    def fix_code(self, code: str, errors: str) -> str:
        """Fix code based on error messages.

        Args:
            code: The code to fix
            errors: Error messages describing issues

        Returns:
            Fixed code as a string
        """
        pass

    @abstractmethod
    def parse_document(self, document: str) -> Dict[str, Any]:
        """Parse a document into structured data.

        Args:
            document: The document content to parse

        Returns:
            Dictionary containing parsed structure
        """
        pass
