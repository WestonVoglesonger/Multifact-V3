# File: backend/test/fixtures/services_fixture.py

import pytest
from sqlalchemy.orm import Session

# Repos
from backend.infrastructure.repositories.document_repository import DocumentRepository
from backend.infrastructure.repositories.token_repository import TokenRepository
from backend.infrastructure.repositories.artifact_repository import ArtifactRepository

# Domain services
from backend.application.services.ni_orchestrator import NIOrchestrator
from backend.application.services.token_diff_service import TokenDiffService
from backend.application.services.document_updater import DocumentUpdater
from backend.application.services.token_compiler import TokenCompiler
from backend.application.services.code_evaluation_service import CodeEvaluationService

# Infrastructure
from backend.infrastructure.services.compilation_service import (
    ConcreteCompilationService,
)
from backend.infrastructure.validation.validation_service import (
    ConcreteValidationService,
)
from backend.infrastructure.llm.llm_service_impl import ConcreteLLMService
from backend.infrastructure.llm.groq_llm_client import GroqLLMClient
from backend.infrastructure.llm.model_factory import GroqModelType, OpenAIModelType
from backend.infrastructure.llm.model_factory import ModelFactory
from backend.infrastructure.llm.model_factory import ClientType

@pytest.fixture
def ni_orchestrator(db_session: Session) -> NIOrchestrator:
    """
    Builds a fully functional UserInterventionService with real DB-based repositories,
    real or default LLM parser (which you might mock if desired).
    """

    # Repositories
    doc_repo = DocumentRepository(db_session)
    token_repo = TokenRepository(db_session)
    artifact_repo = ArtifactRepository(db_session)

    # LLM parser (ex: default to GPT_4O, or “dummy” if you mock)
    llm_parser = ConcreteLLMService(OpenAIModelType.GPT_4O_MINI)

    # Additional services
    token_diff_svc = TokenDiffService()
    document_updater = DocumentUpdater(doc_repo, token_repo)
    compilation_svc = ConcreteCompilationService(db_session)
    validation_svc = ConcreteValidationService(db_session)
    model_type = ModelFactory.get_model(ClientType.GROQ, GroqModelType.LLAMA_GUARD_3_8B)
    llm_evaluator = GroqLLMClient(model_type)
    evaluation_svc = CodeEvaluationService(llm_evaluator)
    token_compiler = TokenCompiler(compilation_svc, validation_svc, evaluation_svc)

    return NIOrchestrator(
        doc_repo=doc_repo,
        token_repo=token_repo,
        artifact_repo=artifact_repo,
        llm_parser=llm_parser,
        token_diff_service=token_diff_svc,
        document_updater=document_updater,
        token_compiler=token_compiler,
    )
