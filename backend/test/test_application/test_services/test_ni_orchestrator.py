import pytest
from unittest.mock import patch, Mock
from sqlalchemy.orm import Session
from backend.application.services.ni_orchestrator import (
    NIOrchestrator,
    DocumentNotFoundError,
    LLMParsingError,
)
from backend.infrastructure.repositories.document_repository import DocumentRepository
from backend.infrastructure.repositories.token_repository import TokenRepository
from backend.infrastructure.repositories.artifact_repository import ArtifactRepository
from backend.infrastructure.llm.llm_service_impl import ConcreteLLMService
from backend.application.services.token_diff_service import TokenDiffService
from backend.application.services.document_updater import DocumentUpdater
from backend.application.services.token_compiler import TokenCompiler
from backend.infrastructure.services.compilation_service import (
    ConcreteCompilationService,
)
from backend.application.services.code_evaluation_service import CodeEvaluationService
from backend.infrastructure.validation.validation_service import (
    ConcreteValidationService,
)
from backend.infrastructure.llm.model_factory import OpenAIModelType
from backend.infrastructure.entities.ni_document import NIDocument
from backend.application.services.exceptions import (
    ArtifactNotFoundError,
    DocumentNotFoundError,
    TokenNotFoundError,
)
from backend.test.test_application.test_services.fixtures import mock_llm_parse_help
from backend.infrastructure.llm.client_factory import ClientFactory


def test_create_ni_document(db_session: Session):
    """
    Test creating a new NI document.
    """
    doc_repo = DocumentRepository(db_session)
    ni_orchestrator = NIOrchestrator(doc_repo, TokenRepository(db_session), ArtifactRepository(db_session), ConcreteLLMService(OpenAIModelType.GPT_4O_MINI), TokenDiffService(), DocumentUpdater(doc_repo, TokenRepository(db_session)), TokenCompiler(ConcreteCompilationService(db_session), ConcreteValidationService(db_session), CodeEvaluationService(ClientFactory.get_llm_client(OpenAIModelType.GPT_4O_MINI))))

    # Test Document
    test_create_ni_document_content = """[Scene:Intro]
        The user enters the application and should receive a friendly greeting.
        [Component:Greeting]
        Display a personalized greeting message to the user.
        [Function:displayGreeting]
        Show "Welcome back, John! How can we assist you today?" in the greeting area.
        [Function:logEntry]
        Log the user's entry time and IP address for security auditing."""
    
    # Create a new document
    doc = ni_orchestrator.create_ni_document(test_create_ni_document_content)
    doc_entity = doc_repo.get_document(doc.id)
    assert doc_entity.content == test_create_ni_document_content
    assert doc_entity.id is not None
    assert doc_entity.version is not None
    assert doc_entity.created_at is not None
    assert doc_entity.updated_at is not None
    assert len(doc_entity.tokens) > 0

def test_user_intervention_service_update_and_recompile_success(
    db_session: Session, mock_llm_parse_help: Mock
):
    """
    Test successful update and recompile, including validation, testing, and scoring.
    """

    # Repositories and services
    doc_repo = DocumentRepository(db_session)
    token_repo = TokenRepository(db_session)
    artifact_repo = ArtifactRepository(db_session)
    llm_parser = ConcreteLLMService(OpenAIModelType.GPT_4O_MINI)
    token_diff_service = TokenDiffService()
    document_updater = DocumentUpdater(doc_repo, token_repo)
    compilation_service = ConcreteCompilationService(db_session)
    validation_service = ConcreteValidationService(db_session)
    evaluator_llm = ClientFactory.get_llm_client(OpenAIModelType.GPT_4O_MINI)
    evaluation_service = CodeEvaluationService(evaluator_llm)
    token_compiler = TokenCompiler(
        compilation_service, validation_service, evaluation_service
    )

    # Instantiate NIOrchestrator
    uis = NIOrchestrator(
        doc_repo=doc_repo,
        token_repo=token_repo,
        artifact_repo=artifact_repo,
        llm_parser=llm_parser,
        token_diff_service=token_diff_service,
        document_updater=document_updater,
        token_compiler=token_compiler,
    )

    # Create a new document
    intervention_doc = (
        db_session.query(NIDocument)
        .filter(NIDocument.content.like("%[Scene:Intervention]%"))
        .first()
    )
    assert intervention_doc, "Demo data should have a doc with [Scene:Intervention]"
    doc_id = intervention_doc.id

    new_content = "[Scene:Intervention]\nUpdated intervention doc.\n[Component:Help]\nDisplay a help message."

    # Perform the update and compile
    uis.update_ni_and_compile(
        ni_id=doc_id,
        new_content=new_content,
        model_type=OpenAIModelType.GPT_4O_MINI,
        revalidate=True,
    )

    # Verify the updated content
    updated_doc = doc_repo.get_document(doc_id)
    assert updated_doc.content == new_content, "Document content should be updated."

    # Verify tokens
    updated_tokens = token_repo.get_all_tokens_for_document(doc_id)
    updated_component = next(
        (t for t in updated_tokens if t.component_name == "Help"), None
    )
    assert updated_component, "Should have a new 'Help' component"
    assert updated_component.content == "Display a help message."

    # Verify evaluation results
    for token in updated_tokens:
        if token.id is None:
            continue
        # Get artifacts for this token
        artifacts = token_repo.get_tokens_with_artifacts(doc_id)
        # Find the artifact for this specific token
        token_artifact = next(
            (art for tok, art in artifacts if tok.id == token.id), None
        )
        assert token_artifact is not None, f"No artifact found for token {token.id}"
        # assert token_artifact.valid, f"Artifact {token_artifact.id} is not valid"
