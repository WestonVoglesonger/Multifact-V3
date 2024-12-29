# File: backend/test/fixtures/services_fixture.py

import pytest
from sqlalchemy.orm import Session

# Repos
from snc.infrastructure.repositories.document_repository import DocumentRepository
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository

# Domain services
from snc.application.services.ni_orchestrator import NIOrchestrator
from snc.application.services.token_diff_service import TokenDiffService
from snc.application.services.document_updater import DocumentUpdater
from snc.application.services.token_compiler import TokenCompiler
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.application.services.self_repair_service import SelfRepairService

# Infrastructure
from snc.infrastructure.services.compilation_service import (
    ConcreteCompilationService,
)
from snc.infrastructure.validation.validation_service import (
    ConcreteValidationService,
)
from snc.infrastructure.llm.llm_service_impl import ConcreteLLMService
from snc.infrastructure.services.code_fixer_service import ConcreteCodeFixerService
from snc.infrastructure.llm.groq_llm_client import GroqLLMClient
from snc.infrastructure.llm.model_factory import GroqModelType, OpenAIModelType
from snc.infrastructure.llm.model_factory import ModelFactory
from snc.infrastructure.llm.model_factory import ClientType


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
    evaluation_svc = CodeEvaluationService(llm_client=llm_evaluator)
    token_compiler = TokenCompiler(
        compilation_svc,
        validation_svc,
        evaluation_svc,
        session=db_session,
    )

    return NIOrchestrator(
        doc_repo=doc_repo,
        token_repo=token_repo,
        artifact_repo=artifact_repo,
        llm_parser=llm_parser,
        token_diff_service=token_diff_svc,
        document_updater=document_updater,
        token_compiler=token_compiler,
    )


@pytest.fixture
def mock_self_repair_service(db_session: Session) -> SelfRepairService:
    # Repositories
    code_fixer_svc = ConcreteCodeFixerService()
    validation_svc = ConcreteValidationService(db_session)
    artifact_repo = ArtifactRepository(db_session)

    return SelfRepairService(
        code_fixer_service=code_fixer_svc,
        validation_service=validation_svc,
        artifact_repo=artifact_repo,
        session=db_session,
    )


@pytest.fixture
def real_self_repair_service(db_session: Session) -> SelfRepairService:
    # Repositories
    code_fixer_svc = ConcreteCodeFixerService()
    validation_svc = ConcreteValidationService(db_session)
    artifact_repo = ArtifactRepository(db_session)

    return SelfRepairService(
        code_fixer_service=code_fixer_svc,
        validation_service=validation_svc,
        artifact_repo=artifact_repo,
        session=db_session,
    )
