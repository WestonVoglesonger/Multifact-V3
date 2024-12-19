# backend/services/validation/validators/base.py
from abc import ABC, abstractmethod
from typing import List
from backend.services.validation.validation_service import ValidationError

class CodeValidator(ABC):
    """
    Abstract base class for language-specific validators.
    Each validator must implement these methods.
    """

    @abstractmethod
    def run_syntax_type_check(self, code: str) -> List[ValidationError]:
        """
        Run language-specific compilation/lint checks and return a list of ValidationErrors.
        """
        pass

    @abstractmethod
    def run_semantic_checks(self, code: str, expectations: dict) -> List[ValidationError]:
        """
        Run semantic checks based on NI expectations and return a list of ValidationErrors.
        """
        pass