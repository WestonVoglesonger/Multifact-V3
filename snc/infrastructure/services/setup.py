"""
Helper module for setting up services with minimal configuration.
"""

from dataclasses import dataclass
from sqlalchemy.orm import Session

from snc.infrastructure.repositories.setup import Repositories
from snc.infrastructure.llm.llm_service_impl import ConcreteLLMService
from snc.application.services.token_diff_service import TokenDiffService
from snc.application.services.document_updater import DocumentUpdater
from snc.application.services.token_compiler import TokenCompiler
from snc.infrastructure.services.compilation_service import ConcreteCompilationService
from snc.infrastructure.validation.validation_service import ConcreteValidationService
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.infrastructure.llm.model_factory import OpenAIModelType


@dataclass
class Services:
    llm_service: ConcreteLLMService
    token_diff_service: TokenDiffService
    document_updater: DocumentUpdater
    token_compiler: TokenCompiler
    validation_service: ConcreteValidationService
    compilation_service: ConcreteCompilationService
    code_evaluation_service: CodeEvaluationService


def setup_services(
    session: Session,
    repositories: Repositories,
    model_type: OpenAIModelType = OpenAIModelType.GPT_4O_MINI,
) -> Services:
    """
    Set up services with minimal configuration.

    Args:
        session: Database session
        repositories: Repository instances
        model_type: OpenAI model type to use

    Returns:
        Services instance with all required services
    """
    llm_service = ConcreteLLMService(model_type)
    token_diff_service = TokenDiffService()
    document_updater = DocumentUpdater(
        repositories.document_repo, repositories.token_repo
    )

    validation_service = ConcreteValidationService(session)
    compilation_service = ConcreteCompilationService(session)
    code_evaluation_service = CodeEvaluationService()

    token_compiler = TokenCompiler(
        compilation_service,
        validation_service,
        code_evaluation_service,
    )

    return Services(
        llm_service=llm_service,
        token_diff_service=token_diff_service,
        document_updater=document_updater,
        token_compiler=token_compiler,
        validation_service=validation_service,
        compilation_service=compilation_service,
        code_evaluation_service=code_evaluation_service,
    )