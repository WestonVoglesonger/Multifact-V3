"""Base class for code validators."""

from abc import ABC, abstractmethod
from typing import List, Dict
from snc.application.interfaces.ivalidation_service import ValidationError


class CodeValidator(ABC):
    """Abstract base class for language-specific validators.
    
    Each validator must implement:
    - run_syntax_type_check: For syntax and type checking
    - run_semantic_checks: For semantic validation
    """

    @abstractmethod
    def run_syntax_type_check(
        self, code: str, strict_mode: bool = False
    ) -> List[ValidationError]:
        """Run syntax and type checking on code.
        
        Args:
            code: Code to check
            strict_mode: Whether to use strict mode
            
        Returns:
            List of validation errors
        """
        pass

    @abstractmethod
    def run_semantic_checks(
        self, code: str, expectations: Dict[str, List[str]]
    ) -> List[ValidationError]:
        """Run semantic validation checks on code.
        
        Args:
            code: Code to check
            expectations: Expected components and methods
            
        Returns:
            List of validation errors
        """
        pass
