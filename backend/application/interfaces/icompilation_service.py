from abc import ABC, abstractmethod
from backend.domain.models import DomainCompiledMultifact
from backend.infrastructure.llm.groq_llm_client import GroqLLMClient
from backend.infrastructure.llm.openai_llm_client import OpenAILLMClient
from sqlalchemy.orm import Session


class ICompilationService(ABC):
    @abstractmethod
    def compile_document(self, doc_id: int) -> dict:
        pass

    @abstractmethod
    def compile_token_with_dependencies(
        self, token_id: int, compiled_artifacts: dict
    ) -> str:
        pass

    @abstractmethod
    def compile_token(
        self, token_id: int, llm_client: GroqLLMClient | OpenAILLMClient
    ) -> DomainCompiledMultifact:
        pass

    @abstractmethod
    def mark_artifact_invalid(self, artifact_id: int) -> None:
        pass

    @abstractmethod
    def update_artifact(self, artifact: DomainCompiledMultifact) -> None:
        pass

    @abstractmethod
    def get_session(self) -> Session:
        """Get the current database session."""
        pass
