from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ILLMClient(ABC):
    """Interface for LLM clients that can be used for code generation and evaluation."""

    @abstractmethod
    def generate_code(self, prompt: str, **kwargs: Any) -> str:
        """Generate code based on a prompt."""
        pass

    @abstractmethod
    def evaluate_code(self, code: str, requirements: str) -> Dict[str, Any]:
        """Evaluate code against requirements."""
        pass

    @abstractmethod
    def fix_code(self, code: str, errors: str) -> str:
        """Fix code based on error messages."""
        pass

    @abstractmethod
    def parse_document(self, document: str) -> Dict[str, Any]:
        """Parse a document into structured data."""
        pass
