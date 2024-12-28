"""
Quick Start Example for System Narrative Compiler (SNC)
This example shows the minimal setup required to get started with SNC.
"""

from snc.application.services.ni_orchestrator import NIOrchestrator
from snc.config import get_settings
from snc.infrastructure.llm.model_factory import OpenAIModelType
from snc.infrastructure.repositories.setup import setup_repositories
from snc.infrastructure.services.setup import setup_services


def main():
    # Load configuration from environment variables
    settings = get_settings()

    # Quick setup of database and services (uses SQLite by default)
    session, repositories = setup_repositories()
    services = setup_services(session, repositories)

    # Initialize orchestrator with minimal configuration
    orchestrator = NIOrchestrator(
        doc_repo=repositories.document_repo,
        token_repo=repositories.token_repo,
        artifact_repo=repositories.artifact_repo,
        llm_parser=services.llm_service,
        token_diff_service=services.token_diff_service,
        document_updater=services.document_updater,
        token_compiler=services.token_compiler,
        code_fixer_service=services.llm_service,
    )

    # Create a simple narrative document
    content = """
    [Component:HelloWorld]
    This component displays a simple greeting message.
    It should show "Hello, World!" in a centered div with a blue background.
    """

    # Create and compile the document
    doc = orchestrator.create_ni_document(initial_content=content, version="v1.0")
    print(f"Created document with ID: {doc.id}")

    # Get all tokens and compile them
    tokens = orchestrator.get_document_tokens(doc.id)
    orchestrator.compile_tokens(tokens, OpenAIModelType.GPT_4O_MINI)

    # Display results
    print("\nGenerated artifacts:")
    artifacts = orchestrator.list_tokens_with_artifacts(doc.id)
    for artifact in artifacts:
        print(f"\n{artifact['token_type']}:{artifact['token_name']}")
        print("-" * 40)
        if artifact.get("code"):
            print(artifact["code"])


if __name__ == "__main__":
    main()
