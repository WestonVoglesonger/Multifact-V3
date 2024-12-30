"""Test the NIOrchestrator service."""

import pytest
from unittest.mock import patch, Mock
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from snc.application.services.ni_orchestrator import (
    NIOrchestrator,
)
from snc.infrastructure.repositories.document_repository import DocumentRepository
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository
from snc.infrastructure.llm.llm_service_impl import ConcreteLLMService
from snc.application.services.token_diff_service import TokenDiffService
from snc.application.services.document_updater import DocumentUpdater
from snc.application.services.token_compiler import TokenCompiler
from snc.infrastructure.services.compilation_service import (
    ConcreteCompilationService,
)
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.infrastructure.validation.validation_service import (
    ConcreteValidationService,
)
from snc.infrastructure.llm.model_factory import OpenAIModelType
from snc.infrastructure.entities.ni_document import NIDocument
from snc.infrastructure.llm.client_factory import ClientFactory
from snc.domain.models import DomainDocument
from snc.infrastructure.llm.openai_llm_client import OpenAILLMClient
from snc.infrastructure.llm.model_factory import ModelFactory, ClientType
from snc.domain.model_types import OpenAIModelType
from snc.test.test_application.test_services.fixtures import (
    mock_llm_parse_help,
    mock_validation_service_failure,
    mock_validation_service_success,
)
from sqlalchemy.orm import sessionmaker


def get_test_session():
    engine = create_engine("sqlite:///:memory:")
    return Session(engine)


@pytest.fixture
def mock_llm_generate_code():
    """Mock the LLM client to generate code for artifacts."""
    with patch.object(ClientFactory, "get_llm_client") as mock_factory:
        mock_client = Mock()
        mock_client.generate_code.return_value = (
            "function displayGreeting() { console.log('Hello!'); }"
        )
        mock_factory.return_value = mock_client
        yield mock_client


def test_create_ni_document(db_session: Session):
    """
    Test creating a new NI document.
    """
    # Create session factory
    session_factory = sessionmaker(bind=db_session.get_bind())

    # Setup repositories
    doc_repo = DocumentRepository(db_session)
    token_repo = TokenRepository(db_session)
    model = ModelFactory.get_model(ClientType.OPENAI, OpenAIModelType.GPT_4O_MINI)
    llm_client = OpenAILLMClient(model=model)
    compilation_service = ConcreteCompilationService(db_session)
    validation_service = ConcreteValidationService(db_session)
    ni_orchestrator = NIOrchestrator(
        doc_repo,
        token_repo,
        ArtifactRepository(db_session),
        ConcreteLLMService(OpenAIModelType.GPT_4O_MINI),
        TokenDiffService(),
        DocumentUpdater(doc_repo, token_repo),
        TokenCompiler(
            compilation_service=compilation_service,
            validation_service=validation_service,
            session_factory=session_factory,
            token_repository=token_repo,
        ),
    )

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
    doc_ent = NIDocument(content="", version="v1")
    db_session.add(doc_ent)
    db_session.commit()

    # Update the document
    ni_orchestrator.update_ni_and_compile(
        ni_id=doc_ent.id,
        new_content=test_create_ni_document_content,
        model_type=OpenAIModelType.GPT_4O_MINI,
        revalidate=True,
    )

    doc_entity = doc_repo.get_document(doc_ent.id)
    assert doc_entity is not None, "Document should exist"
    assert doc_entity.content == test_create_ni_document_content
    assert doc_entity.id is not None
    assert doc_entity.version is not None
    assert doc_entity.created_at is not None
    assert doc_entity.updated_at is not None
    assert len(doc_entity.tokens) > 0
    # Check specific tokens
    assert any(t.token_type == "scene" and t.scene_name == "Intro" for t in doc_entity.tokens)
    assert any(
        t.token_type == "component" and t.component_name == "Greeting" for t in doc_entity.tokens
    )
    assert any(
        t.token_type == "function" and t.function_name == "displayGreeting"
        for t in doc_entity.tokens
    )
    assert any(
        t.token_type == "function" and t.function_name == "logEntry" for t in doc_entity.tokens
    )


def test_user_intervention_service_update_and_recompile_success(
    db_session: Session,
    mock_llm_parse_help: Mock,
    mock_llm_generate_code: Mock,
    mock_validation_service_success: Mock,
):
    """
    Test successful update and recompile, including validation, testing, and scoring.
    """

    # Create session factory
    session_factory = sessionmaker(bind=db_session.get_bind())

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
    evaluation_service = CodeEvaluationService(
        llm_client=evaluator_llm, validation_service=validation_service
    )
    token_compiler = TokenCompiler(
        compilation_service=compilation_service,
        validation_service=validation_service,
        session_factory=session_factory,
        token_repository=token_repo,
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

    new_content = (
        "[Scene:Intervention]\nUpdated intervention doc.\n[Component:Help]\nDisplay a help message."
    )

    # Perform the update and compile
    uis.update_ni_and_compile(
        ni_id=doc_id,
        new_content=new_content,
        model_type=OpenAIModelType.GPT_4O_MINI,
        revalidate=True,
    )

    # Verify the updated content
    updated_doc = doc_repo.get_document(doc_id)
    assert updated_doc is not None, "Document should exist"
    assert isinstance(updated_doc, DomainDocument), "Document should be a DomainDocument"
    doc: DomainDocument = updated_doc  # Type cast after assertion
    assert doc.content == new_content, "Document content should be updated."

    # Verify tokens
    updated_tokens = token_repo.get_all_tokens_for_document(doc_id)
    updated_component = next((t for t in updated_tokens if t.component_name == "Help"), None)
    assert updated_component is not None, "Should have a new 'Help' component"
    assert updated_component.content == "[Component:Help]\nDisplay a help message."

    # Wait for compilation to complete and verify artifacts
    db_session.expire_all()  # Ensure we get fresh data
    artifacts_by_token = token_repo.get_tokens_with_artifacts(doc_id)
    for token in updated_tokens:
        if token.id is None:
            continue
        # Find the artifact for this specific token
        token_artifact = next((art for tok, art in artifacts_by_token if tok.id == token.id), None)
        assert token_artifact is not None, f"No artifact found for token {token.id}"
        # assert token_artifact.valid, f"Artifact {token_artifact.id} is not valid"
