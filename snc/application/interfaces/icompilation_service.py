"""Interface for the compilation service."""

from abc import ABC, abstractmethod
from snc.domain.models import DomainCompiledMultifact
from snc.domain.model_types import CompilationResult


class ICompilationService(ABC):
    """Interface for compilation service."""

    @abstractmethod
    def compile(self, code: str) -> CompilationResult:
        """Compile code and return the result."""
        pass
