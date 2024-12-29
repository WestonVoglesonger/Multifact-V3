"""Interface for code fixing service."""

from abc import ABC, abstractmethod


class ICodeFixerService(ABC):
    """Service interface for fixing code based on error feedback."""

    @abstractmethod
    def fix_code(self, original_code: str, error_summary: str) -> str:
        """Fix the given code based on error feedback.

        Args:
            original_code: The code to fix
            error_summary: Description of the errors to fix

        Returns:
            The fixed code as a string
        """
        pass
