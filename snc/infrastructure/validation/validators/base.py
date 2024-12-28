from abc import ABC, abstractmethod
from typing import List
from snc.application.interfaces.ivalidation_service import ValidationError


class CodeValidator(ABC):
    """
    Abstract base class for language-specific validators.
    Each validator must implement these methods.
    """

    @abstractmethod
    def run_syntax_type_check(
        self, code: str, strict_mode: bool = False
    ) -> List[ValidationError]:
        """Run syntax and type checking on code."""
        pass

    @abstractmethod
    def run_semantic_checks(
        self, code: str, expectations: dict
    ) -> List[ValidationError]:
        """Run semantic validation checks on code."""
        pass
