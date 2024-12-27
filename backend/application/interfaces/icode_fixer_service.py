from abc import ABC, abstractmethod


class ICodeFixerService(ABC):
    @abstractmethod
    def fix_code(self, original_code: str, error_summary: str) -> str:
        """
        Fix the given code and return the fixed code.
        """
