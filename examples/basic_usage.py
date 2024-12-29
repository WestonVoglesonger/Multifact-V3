"""
Basic example demonstrating how to use System Narrative Compiler (SNC) for narrative instruction processing.
"""

from sqlalchemy.orm import Session
from snc.infrastructure.repositories.document_repository import DocumentRepository
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository
from snc.infrastructure.llm.llm_service_impl import ConcreteLLMService
from snc.application.services.token_diff_service import TokenDiffService
from snc.application.services.document_updater import DocumentUpdater
from snc.application.services.token_compiler import TokenCompiler
from snc.infrastructure.services.code_fixer_service import ConcreteCodeFixerService
from snc.infrastructure.services.compilation_service import ConcreteCompilationService
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.infrastructure.validation.validation_service import ConcreteValidationService
from snc.infrastructure.llm.model_factory import OpenAIModelType
from snc.application.services.ni_orchestrator import NIOrchestrator
from snc.application.services.dependency_graph_service import DependencyGraphService
from snc.application.services.self_repair_service import SelfRepairService
from snc.infrastructure.entities.entity_base import EntityBase
from snc.infrastructure.entities.ni_document import NIDocument
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.services.code_fixer_service import ConcreteCodeFixerService


def main():
    # Create a database session using our PostgreSQL setup
    from snc.database import db_session, engine

    # Drop and recreate all tables
    EntityBase.metadata.drop_all(engine)
    EntityBase.metadata.create_all(engine)

    # Get a session
    session = next(db_session())

    # Initialize repositories
    doc_repo = DocumentRepository(session)
    token_repo = TokenRepository(session)
    artifact_repo = ArtifactRepository(session)

    # Initialize services
    llm_service = ConcreteLLMService(OpenAIModelType.GPT_4O_MINI)
    token_diff_service = TokenDiffService()
    document_updater = DocumentUpdater(doc_repo, token_repo)
    validation_service = ConcreteValidationService(session)
    compilation_service = ConcreteCompilationService(session)
    code_evaluation_service = CodeEvaluationService()
    token_compiler = TokenCompiler(
        compilation_service,
        validation_service,
        code_evaluation_service,
    )
    code_fixer_service = ConcreteCodeFixerService()

    # Initialize self-repair service
    self_repair_service = SelfRepairService(
        artifact_repo=artifact_repo,
        validation_service=validation_service,
        code_fixer_service=code_fixer_service,
        session=session,
    )

    # Initialize orchestrator
    orchestrator = NIOrchestrator(
        doc_repo=doc_repo,
        token_repo=token_repo,
        artifact_repo=artifact_repo,
        llm_parser=llm_service,
        token_diff_service=token_diff_service,
        document_updater=document_updater,
        token_compiler=token_compiler,
        code_fixer_service=code_fixer_service,
    )

    # Create a simple narrative document
    content = """
    [Scene:LoginScene]
    This scene handles user login functionality.
    
    [Function:validateInput]
    This function validates the user's input for username and password.
    
    [Function:authenticate]
    This function [REF:validateInput] authenticates the user by first validating their input.
    
    [Component:LoginForm]
    This component [REF:authenticate] provides a form for user login and handles authentication.
    """

    # Create the document
    doc = orchestrator.create_ni_document(initial_content=content, version="v1.0")
    print(f"\nCreated document with ID: {doc.id}")

    # Analyze dependencies
    graph_service = DependencyGraphService(token_repo)
    graph_service.from_document(doc.id)

    # Get compilation order
    order = graph_service.topological_sort()
    print("\nCompilation order:")
    tokens_to_compile = []
    for token_id in order:
        token = token_repo.get_token_by_id(token_id)
        if token:
            print(f"- {token.token_type}:{token.token_name}")
            tokens_to_compile.append(token)

    # Compile tokens
    print("\nCompiling tokens...")
    orchestrator.compile_tokens(tokens_to_compile, OpenAIModelType.GPT_4O_MINI)

    # Get artifacts and attempt repair if needed
    print("\nChecking for artifacts that need repair...")
    artifacts = orchestrator.list_tokens_with_artifacts(doc.id)
    for artifact_info in artifacts:
        if not artifact_info.get(
            "valid", True
        ):  # Try to repair if not explicitly valid
            artifact_id = artifact_info["artifact_id"]
            if artifact_id:
                print(f"\nAttempting to repair artifact {artifact_id}...")
                success = self_repair_service.repair_artifact(artifact_id)
                if success:
                    print(f"Successfully repaired artifact {artifact_id}")
                else:
                    print(f"Failed to repair artifact {artifact_id}")

    # Show final results
    print("\nFinal artifacts:")
    artifacts = orchestrator.list_tokens_with_artifacts(doc.id)
    for artifact_info in artifacts:
        token_id = artifact_info.get("token_id")
        token = token_repo.get_token_by_id(token_id) if token_id is not None else None
        token_type = token.token_type if token else "unknown"
        token_name = token.token_name if token else "unnamed"
        print(f"\n{token_type}:{token_name}")
        print("-" * 40)
        if artifact_info.get("artifact_id"):
            print(f"Valid: {artifact_info.get('valid', False)}")
            code = artifact_info.get("code", "")
            if code:
                print(code[:200] + "..." if len(code) > 200 else code)
            else:
                print("No code available")
        else:
            print("No artifact generated")


if __name__ == "__main__":
    main()
