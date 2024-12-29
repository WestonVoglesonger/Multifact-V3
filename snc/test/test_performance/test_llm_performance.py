# File: snc/test/test_performance/test_llm_performance.py

import os
import pytest
import logging
from typing import Callable, Any
from sqlalchemy.orm import Session

# External references in your codebase:
from snc.test.test_performance.test_performance_data import TEST_INPUTS

# Services needed:
from snc.application.services.ni_orchestrator import NIOrchestrator
from snc.application.services.token_diff_service import TokenDiffService
from snc.application.services.document_updater import DocumentUpdater
from snc.application.services.token_compiler import TokenCompiler
from snc.infrastructure.services.compilation_service import ConcreteCompilationService
from snc.infrastructure.validation.validation_service import ConcreteValidationService
from snc.application.services.code_evaluation_service import CodeEvaluationService

# Repositories:
from snc.infrastructure.repositories.document_repository import DocumentRepository
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository

# LLM-related:
from snc.infrastructure.llm.llm_service_impl import ConcreteLLMService
from snc.infrastructure.llm.client_factory import ClientFactory
from snc.infrastructure.llm.model_factory import ClientType
from snc.domain.model_types import GroqModelType, OpenAIModelType
from snc.infrastructure.llm.base_llm_client import BaseLLMClient
from snc.infrastructure.llm.groq_llm_client import GroqLLMClient
from snc.infrastructure.llm.openai_llm_client import OpenAILLMClient

# Entities:
from snc.infrastructure.entities.ni_document import NIDocument

logging.basicConfig(level=logging.INFO)

# Provide each test input a descriptive ID for test reports
input_ids = [f"input_{i+1}" for i in range(len(TEST_INPUTS))]


def _build_llm_client_from_env() -> BaseLLMClient:
    """
    Reads LLM_CLIENT_TYPE & LLM_MODEL_TYPE from environment
    and constructs a suitable LLM client (BaseLLMClient).
    """
    client_type_str = os.getenv("LLM_CLIENT_TYPE", "openai").lower()
    model_type_str = os.getenv("LLM_MODEL_TYPE", "gpt-4o").lower()

    if client_type_str == "openai":
        return _build_openai_client(model_type_str)
    elif client_type_str == "groq":
        return _build_groq_client(model_type_str)
    else:
        raise ValueError(f"Unknown LLM client type: '{client_type_str}'")


def _build_openai_client(model_type_str: str) -> OpenAILLMClient:
    if model_type_str == "gpt-4o":
        return ClientFactory.get_llm_client(OpenAIModelType.GPT_4O)  # type: ignore
    elif model_type_str == "gpt-4o-mini":
        return ClientFactory.get_llm_client(OpenAIModelType.GPT_4O_MINI)  # type: ignore
    else:
        raise ValueError(f"Unknown or unsupported OpenAI model: '{model_type_str}'")


def _build_groq_client(model_type_str: str) -> GroqLLMClient:
    if model_type_str == "llama-guard-3-8b":
        return ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)  # type: ignore
    elif model_type_str == "llama-3.1-8b-instant":
        return ClientFactory.get_llm_client(GroqModelType.LLAMA_3_1_8B_INSTANT)  # type: ignore
    else:
        raise ValueError(f"Unknown or unsupported Groq model: '{model_type_str}'")


@pytest.mark.benchmark(group="doc_creation_varied")
@pytest.mark.parametrize("ni_content", TEST_INPUTS, ids=input_ids)
def test_ni_creation_and_compilation(
    benchmark: Callable[[Callable[[], Any]], Any],
    db_session: Session,
    ni_content: str,
) -> None:
    """
    Test creating and compiling NI documents from various realistic narrative instructions.
    We build the LLM client from environment variables each run, so that benchmark_all_models.py
    can set (LLM_CLIENT_TYPE, LLM_MODEL_TYPE) and call this test repeatedly.
    """

    # Build the LLM client from environment variables
    llm_client = _build_llm_client_from_env()

    def create_and_compile():
        # 1) Insert a doc in DB with a placeholder
        doc_ent = NIDocument(
            content="[Scene:Placeholder]\nThis content will be replaced by NI content.",
            version="v1",
        )
        db_session.add(doc_ent)
        db_session.commit()

        doc_id = doc_ent.id

        # 2) Setup the pipeline
        doc_repo = DocumentRepository(db_session)
        token_repo = TokenRepository(db_session)
        artifact_repo = ArtifactRepository(db_session)

        # Example LLM parser usage
        parser_llm = ConcreteLLMService(model_type=OpenAIModelType.GPT_4O_MINI)
        token_diff_service = TokenDiffService()
        document_updater = DocumentUpdater(doc_repo, token_repo)
        compilation_service = ConcreteCompilationService(db_session)
        validation_service = ConcreteValidationService(db_session)
        evaluation_service = CodeEvaluationService()  # No llm_client needed
        token_compiler = TokenCompiler(
            compilation_service, validation_service, evaluation_service
        )

        uis = NIOrchestrator(
            doc_repo=doc_repo,
            token_repo=token_repo,
            artifact_repo=artifact_repo,
            llm_parser=parser_llm,
            token_diff_service=token_diff_service,
            document_updater=document_updater,
            token_compiler=token_compiler,
        )

        # 3) Parse & compile using new_content = ni_content
        try:
            uis.update_ni_and_compile(
                ni_id=doc_id,
                new_content=ni_content,
                model_type=OpenAIModelType.GPT_4O_MINI,
                revalidate=True,
            )
        except Exception as e:
            logging.error(f"Failed to create/compile doc {doc_id} from NI content: {e}")
            raise

        # 4) Gather usage/cost from the (actual) llm_client
        usage_info = {}
        if llm_client.last_usage:
            usage_info = {
                "prompt_tokens": llm_client.last_usage.prompt_tokens,
                "completion_tokens": llm_client.last_usage.completion_tokens,
                "total_tokens": llm_client.last_usage.total_tokens,
                "cost": getattr(llm_client, "last_cost", 0.0),
            }

        # Attach usage info to the benchmark
        benchmark.extra_info = usage_info
        return usage_info

    # Actually run the code inside pytest-benchmark's harness
    benchmark(create_and_compile)
