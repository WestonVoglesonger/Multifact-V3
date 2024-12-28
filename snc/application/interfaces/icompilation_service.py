from abc import ABC, abstractmethod
from snc.domain.models import DomainCompiledMultifact
from snc.domain.model_types import CompilationResult


class ICompilationService(ABC):
    """Interface for compilation service."""

    @abstractmethod
    def compile(self, code: str) -> CompilationResult:
        """Compile code and return the result."""
        pass

    @abstractmethod
    def compile_multifact(
        self, multifact: DomainCompiledMultifact
    ) -> CompilationResult:
        """Compile multifact and return the result."""
        pass
