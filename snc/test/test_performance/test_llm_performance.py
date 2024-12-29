"""Performance tests for LLM-based operations."""

import logging
from typing import Any, Callable, Dict, List, Optional

import pytest
from sqlalchemy.orm import Session

from snc.application.interfaces.illm_client import ILLMClient
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.infrastructure.services.compilation_service import ConcreteCompilationService
from snc.application.services.document_updater import DocumentUpdater
from snc.infrastructure.llm.llm_service_impl import ConcreteLLMService
from snc.application.services.ni_orchestrator import NIOrchestrator
from snc.application.services.token_compiler import TokenCompiler
from snc.application.services.token_diff_service import TokenDiffService
from snc.infrastructure.validation.validation_service import ConcreteValidationService
from snc.database import Session
from snc.infrastructure.entities.ni_document import NIDocument
from snc.infrastructure.llm.base_llm_client import BaseLLMClient
from snc.domain.model_types import OpenAIModelType
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository
from snc.infrastructure.repositories.document_repository import DocumentRepository
from snc.infrastructure.repositories.token_repository import TokenRepository

from .test_performance_data import TEST_INPUTS

logger = logging.getLogger(__name__)

# Create IDs for test inputs to make test output more readable
input_ids = [f"input_{i+1}" for i in range(len(TEST_INPUTS))]


def _build_llm_client_from_env() -> Optional[BaseLLMClient]:
    """Build LLM client from environment variables.

    Returns:
        LLM client if environment variables are set, None otherwise
    """
    import os

    client_type = os.getenv("LLM_CLIENT_TYPE")
    model_type = os.getenv("LLM_MODEL_TYPE")

    if not client_type or not model_type:
        logger.warning("LLM_CLIENT_TYPE and/or LLM_MODEL_TYPE not set, skipping test")
        return None

    if client_type == "openai":
        from snc.infrastructure.llm.openai_llm_client import OpenAILLMClient
        from snc.domain.model_types import OpenAIModelType

        model_enum = getattr(OpenAIModelType, model_type.upper().replace("-", "_"))
        return OpenAILLMClient(model=model_enum)
    elif client_type == "groq":
        from snc.infrastructure.llm.groq_llm_client import GroqLLMClient
        from snc.domain.model_types import GroqModelType

        model_enum = getattr(GroqModelType, model_type.upper().replace("-", "_"))
        return GroqLLMClient(model=model_enum)
    else:
        logger.warning(f"Unknown LLM client type: {client_type}")
        return None


@pytest.mark.benchmark(group="doc_creation_varied")
@pytest.mark.parametrize("ni_content", TEST_INPUTS, ids=input_ids)
def test_ni_creation_and_compilation(
    benchmark: Callable[[Callable[[], Any]], Any],
    db_session: Session,
    ni_content: str,
) -> None:
    """
    Test creating and compiling NI documents from various realistic narrative instructions.
    Requires environment variables:
    - LLM_CLIENT_TYPE: 'openai' or 'groq'
    - LLM_MODEL_TYPE: specific model identifier
    """
    # Build the LLM client from environment variables
    llm_client = _build_llm_client_from_env()
    if llm_client is None:
        pytest.skip("Required LLM environment variables not set")

    def create_and_compile():
        try:
            # Create a fresh session for each test run
            test_session = db_session

            # 1) Insert a doc in DB with a placeholder
            doc_ent = NIDocument(
                content="[Scene:Placeholder]\nThis content will be replaced by NI content.",
                version="v1",
            )
            test_session.add(doc_ent)
            test_session.commit()

            doc_id = doc_ent.id

            # 2) Setup the pipeline
            doc_repo = DocumentRepository(test_session)
            token_repo = TokenRepository(test_session)
            artifact_repo = ArtifactRepository(test_session)

            parser_llm = ConcreteLLMService(model_type=OpenAIModelType.GPT_4O_MINI)
            token_diff_service = TokenDiffService()
            document_updater = DocumentUpdater(doc_repo, token_repo)
            compilation_service = ConcreteCompilationService(test_session)
            validation_service = ConcreteValidationService(test_session)
            evaluation_service = CodeEvaluationService()
            token_compiler = TokenCompiler(
                compilation_service,
                validation_service,
                evaluation_service,
                session_factory=lambda: test_session,
            )

            orchestrator = NIOrchestrator(
                doc_repo=doc_repo,
                token_repo=token_repo,
                artifact_repo=artifact_repo,
                llm_parser=parser_llm,
                token_diff_service=token_diff_service,
                document_updater=document_updater,
                token_compiler=token_compiler,
            )

            # 3) Parse & compile using new_content = ni_content
            orchestrator.update_ni_and_compile(
                ni_id=doc_id,
                new_content=ni_content,
                model_type=OpenAIModelType.GPT_4O_MINI,
                revalidate=True,
            )

            # 4) Gather usage/cost from the llm_client
            usage_info = {}
            if llm_client and llm_client.last_usage:
                usage_info = {
                    "prompt_tokens": llm_client.last_usage.prompt_tokens,
                    "completion_tokens": llm_client.last_usage.completion_tokens,
                    "total_tokens": llm_client.last_usage.total_tokens,
                    "cost": getattr(llm_client, "last_cost", 0.0),
                }

            # Attach usage info to the benchmark
            benchmark.extra_info = usage_info

            return usage_info

        except Exception as e:
            logger.error(f"Error in create_and_compile: {e}")
            raise

    # Run the code inside pytest-benchmark's harness
    benchmark(create_and_compile)
