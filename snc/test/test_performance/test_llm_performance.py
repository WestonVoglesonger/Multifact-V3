# File: snc/test/test_performance/test_llm_performance.py

import os
import pytest
import logging
from typing import Callable, Any, Optional, TypeVar, ParamSpec, cast
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
logger = logging.getLogger(__name__)

# Type variables for the decorator
P = ParamSpec("P")
T = TypeVar("T")

# Provide each test input a descriptive ID for test reports
input_ids = [f"input_{i+1}" for i in range(len(TEST_INPUTS))]


def _build_llm_client_from_env() -> Optional[BaseLLMClient]:
    """
    Reads LLM_CLIENT_TYPE & LLM_MODEL_TYPE from environment
    and constructs a suitable LLM client (BaseLLMClient).
    Returns None if required environment variables are missing.
    """
    client_type_str = os.getenv("LLM_CLIENT_TYPE")
    model_type_str = os.getenv("LLM_MODEL_TYPE")

    if not client_type_str or not model_type_str:
        logger.warning("Missing required environment variables: LLM_CLIENT_TYPE and/or LLM_MODEL_TYPE")
        return None

    client_type_str = client_type_str.lower()
    model_type_str = model_type_str.lower()

    try:
        if client_type_str == "openai":
            return _build_openai_client(model_type_str)
        elif client_type_str == "groq":
            return _build_groq_client(model_type_str)
        else:
            logger.error(f"Unknown LLM client type: '{client_type_str}'")
            return None
    except ValueError as e:
        logger.error(f"Error building LLM client: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error building LLM client: {e}")
        return None


def _build_openai_client(model_type_str: str) -> OpenAILLMClient:
    """Build an OpenAI client with the specified model type."""
    model_map = {
        "gpt-4o": OpenAIModelType.GPT_4O,
        "gpt-4o-mini": OpenAIModelType.GPT_4O_MINI
    }
    
    if model_type_str not in model_map:
        raise ValueError(f"Unknown or unsupported OpenAI model: '{model_type_str}'. Supported models: {list(model_map.keys())}")
    
    return cast(OpenAILLMClient, ClientFactory.get_llm_client(model_map[model_type_str]))


def _build_groq_client(model_type_str: str) -> GroqLLMClient:
    """Build a Groq client with the specified model type."""
    model_map = {
        "llama-guard-3-8b": GroqModelType.LLAMA_GUARD_3_8B,
        "llama-3.1-8b-instant": GroqModelType.LLAMA_3_1_8B_INSTANT
    }
    
    if model_type_str not in model_map:
        raise ValueError(f"Unknown or unsupported Groq model: '{model_type_str}'. Supported models: {list(model_map.keys())}")
    
    return cast(GroqLLMClient, ClientFactory.get_llm_client(model_map[model_type_str]))


def requires_llm(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to skip tests if LLM client cannot be built."""
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        if _build_llm_client_from_env() is None:
            pytest.skip("Required LLM environment variables not set")
        return func(*args, **kwargs)
    return wrapper


@pytest.mark.benchmark(group="doc_creation_varied")
@pytest.mark.parametrize("ni_content", TEST_INPUTS, ids=input_ids)
@requires_llm
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
    assert llm_client is not None, "LLM client should be available due to @requires_llm decorator"

    def create_and_compile():
        try:
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

            parser_llm = ConcreteLLMService(model_type=OpenAIModelType.GPT_4O_MINI)
            token_diff_service = TokenDiffService()
            document_updater = DocumentUpdater(doc_repo, token_repo)
            compilation_service = ConcreteCompilationService(db_session)
            validation_service = ConcreteValidationService(db_session)
            evaluation_service = CodeEvaluationService()
            token_compiler = TokenCompiler(
                compilation_service, validation_service, evaluation_service
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
