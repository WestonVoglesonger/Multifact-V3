"""
Stress test for System Narrative Compiler (SNC) with complex Angular components.
"""

import os
import sys
import time
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snc.infrastructure.llm.openai_llm_client import OpenAILLMClient
from snc.infrastructure.repositories.document_repository import DocumentRepository
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository
from snc.application.services.token_compiler import TokenCompiler
from snc.infrastructure.services.compilation_service import ConcreteCompilationService
from snc.infrastructure.validation.validation_service import ConcreteValidationService
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.infrastructure.db.session import get_session
from snc.infrastructure.db.models import EntityBase
from snc.infrastructure.db.engine import engine
from snc.domain.models import Model
from snc.infrastructure.entities.ni_document import NIDocument
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact


def create_test_document(doc_repo: DocumentRepository) -> int:
    """Create a test document and return its ID."""
    return doc_repo.create_document("Test Document")


def create_test_tokens(token_repo: TokenRepository, doc_id: int) -> None:
    """Create test tokens for the document."""
    tokens = []
    # Create a scene token
    tokens.append(
        {
            "type": "scene",
            "token_name": "MainScene",
            "content": "[Scene:MainScene]\nA beautiful scene with mountains and trees",
        }
    )

    # Create component tokens
    for i in range(5):
        tokens.append(
            {
                "type": "component",
                "token_name": f"Component_{i}",
                "content": f"[Component:Component_{i}]\nA component that does something interesting {i}",
            }
        )

    # Create service tokens
    for i in range(5):
        tokens.append(
            {
                "type": "service",
                "token_name": f"Service_{i}",
                "content": f"[Service:Service_{i}]\nA service that provides functionality {i}",
            }
        )

    token_repo.add_new_tokens(doc_id, tokens)


def get_artifacts(artifact_repo: ArtifactRepository, doc_id: int) -> Dict[str, str]:
    """Get all artifacts for a document."""
    artifacts = {}
    tokens = artifact_repo.get_tokens_with_artifacts(doc_id)
    for token in tokens:
        if token.artifact:
            artifacts[token.token_name] = token.artifact.code
    return artifacts


def compare_artifacts(
    sequential_artifacts: Dict[str, str], parallel_artifacts: Dict[str, str]
) -> None:
    """Compare artifacts between sequential and parallel compilation."""
    print("\nComparing artifacts between sequential and parallel compilation:")
    print("=" * 80)

    all_tokens = set(sequential_artifacts.keys()) | set(parallel_artifacts.keys())
    differences_found = False

    for token_name in sorted(all_tokens):
        seq_code = sequential_artifacts.get(token_name, "")
        par_code = parallel_artifacts.get(token_name, "")

        if seq_code != par_code:
            differences_found = True
            print(f"\nDifferences found in {token_name}:")
            print("-" * 40)
            print("Sequential:")
            print(seq_code)
            print("\nParallel:")
            print(par_code)
            print("-" * 40)

    if not differences_found:
        print("No differences found between sequential and parallel compilation!")


def main():
    """Main function to run the stress test."""
    session = get_session()

    # Initialize repositories and services
    doc_repo = DocumentRepository(session)
    token_repo = TokenRepository(session)
    artifact_repo = ArtifactRepository(session)
    model = Model(
        client_type="openai",
        name="gpt-4o-mini",
        context_window=8192,
        max_output_tokens=4096,
        prompt_cost_per_1k=0.03,
        completion_cost_per_1k=0.06,
        supports_images=False,
        supports_audio=False,
        supports_video=False,
        supports_reasoning=True,
        reasoning_tokens=1.0,
        knowledge_cutoff_date="2023-04-01",
    )
    llm_client = OpenAILLMClient(model)
    compilation_service = ConcreteCompilationService(session)
    validation_service = ConcreteValidationService(session)
    code_evaluation_service = CodeEvaluationService()
    token_compiler = TokenCompiler(
        compilation_service, validation_service, code_evaluation_service
    )

    # Create test document and tokens
    doc_id = create_test_document(doc_repo)
    create_test_tokens(token_repo, doc_id)

    # Get all tokens for compilation
    tokens = token_repo.get_all_tokens_for_document(doc_id)

    # Sequential compilation
    print("\nRunning sequential compilation...")
    start_time = time.time()
    token_compiler.compile_and_validate(tokens, llm_client, revalidate=True)
    sequential_time = time.time() - start_time
    sequential_artifacts = get_artifacts(artifact_repo, doc_id)
    print(f"Sequential compilation completed in {sequential_time:.2f} seconds")

    # Clear artifacts for parallel compilation
    session.query(CompiledMultifact).delete()
    session.query(NIToken).delete()
    session.query(NIDocument).delete()
    session.commit()

    # Recreate test document and tokens
    doc_id = create_test_document(doc_repo)
    create_test_tokens(token_repo, doc_id)
    tokens = token_repo.get_all_tokens_for_document(doc_id)

    # Parallel compilation
    print("\nRunning parallel compilation...")
    start_time = time.time()
    token_compiler.compile_and_validate_parallel(tokens, llm_client, revalidate=True)
    parallel_time = time.time() - start_time
    parallel_artifacts = get_artifacts(artifact_repo, doc_id)
    print(f"Parallel compilation completed in {parallel_time:.2f} seconds")

    # Compare results
    print(f"\nSpeed comparison:")
    print(f"Sequential: {sequential_time:.2f} seconds")
    print(f"Parallel: {parallel_time:.2f} seconds")
    print(f"Speedup: {sequential_time/parallel_time:.2f}x")

    compare_artifacts(sequential_artifacts, parallel_artifacts)


if __name__ == "__main__":
    main()
