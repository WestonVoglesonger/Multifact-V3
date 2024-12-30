"""Service for orchestrating NI document updates and compilation."""

from typing import Dict, Any, cast, List, TYPE_CHECKING

from snc.infrastructure.llm.openai_llm_client import OpenAILLMClient
from snc.infrastructure.llm.llm_service_impl import ConcreteLLMService
from snc.infrastructure.llm.model_factory import OpenAIModelType, ModelFactory, ClientType
from snc.infrastructure.repositories.document_repository import DocumentRepository
from snc.application.interfaces.idocument_repository import IDocumentRepository
from snc.application.interfaces.itoken_repository import ITokenRepository
from snc.application.interfaces.iartifact_repository import IArtifactRepository
from snc.application.services.token_compiler import TokenCompiler
from snc.application.services.document_updater import DocumentUpdater
from snc.application.services.token_diff_service import TokenDiffService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from snc.domain.models import DomainToken


class NIOrchestrator:
    """Service for orchestrating NI document updates and compilation."""

    def __init__(
        self,
        doc_repo: IDocumentRepository,
        token_repo: ITokenRepository,
        artifact_repo: IArtifactRepository,
        llm_parser: ConcreteLLMService,
        token_diff_service: TokenDiffService,
        document_updater: DocumentUpdater,
        token_compiler: TokenCompiler,
    ):
        """Initialize the orchestrator.

        Args:
            doc_repo: Repository for NI documents
            token_repo: Repository for tokens
            artifact_repo: Repository for compiled artifacts
            llm_parser: Service for parsing NI content
            token_diff_service: Service for diffing tokens
            document_updater: Service for updating documents
            token_compiler: Service for compiling tokens
        """
        self.doc_repo = doc_repo
        self.token_repo = token_repo
        self.artifact_repo = artifact_repo
        self.llm_parser = llm_parser
        self.token_diff_service = token_diff_service
        self.document_updater = document_updater
        self.token_compiler = token_compiler

    def _flatten_llm_output(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert hierarchical LLM output into a flat list of tokens.

        Args:
            data: Parsed LLM output

        Returns:
            List of token dictionaries
        """
        result = []
        for scene in data.get("scenes", []):
            scene_name = scene.get("name", "UnnamedScene")
            scene_narrative = scene.get("narrative", "")

            # Scene token
            result.append(
                {
                    "type": "scene",
                    "token_name": scene_name,
                    "scene_name": scene_name,
                    "component_name": None,
                    "function_name": None,
                    "content": scene_narrative,
                }
            )

            # Functions
            for func in scene.get("functions", []):
                func_name = func.get("name", "UnnamedFunction")
                func_narrative = func.get("narrative", "")
                result.append(
                    {
                        "type": "function",
                        "token_name": func_name,
                        "scene_name": None,
                        "component_name": None,
                        "function_name": func_name,
                        "content": func_narrative,
                    }
                )

            # Components
            for comp in scene.get("components", []):
                comp_name = comp.get("name", "UnnamedComponent")
                comp_narrative = comp.get("narrative", "")
                result.append(
                    {
                        "type": "component",
                        "token_name": comp_name,
                        "scene_name": None,
                        "component_name": comp_name,
                        "function_name": None,
                        "content": comp_narrative,
                    }
                )

        return result

    def update_ni_and_compile(
        self,
        ni_id: int,
        new_content: str,
        model_type: OpenAIModelType,
        revalidate: bool = True,
    ) -> None:
        """Update NI document content and compile any new/changed tokens.

        Args:
            ni_id: ID of NI document to update
            new_content: New content to set
            model_type: LLM model type to use
            revalidate: Whether to validate compiled artifacts
        """
        # Get document
        doc = self.doc_repo.get_document(ni_id)
        if not doc:
            raise ValueError(f"Document with id {ni_id} not found")

        # Update content
        doc.content = new_content

        # Parse new tokens
        model = ModelFactory.get_model(ClientType.OPENAI, model_type)
        llm_client = OpenAILLMClient(model)

        # Get existing tokens with their artifacts
        existing_tokens = self.token_repo.get_tokens_with_artifacts(ni_id)

        # Parse new content into token data
        parsed_data = self.llm_parser.parse_document(new_content)
        new_token_data = self._flatten_llm_output(parsed_data)

        # Calculate diff
        diff_result = self.token_diff_service.diff_tokens(existing_tokens, new_token_data)

        # Apply diff to update tokens
        added_tokens = self.document_updater.apply_diff(ni_id, new_content, diff_result)

        # Commit to ensure tokens are in DB before compilation
        if isinstance(self.doc_repo, DocumentRepository):
            cast(DocumentRepository, self.doc_repo).session.commit()

        # Now compile tokens
        if added_tokens:
            self.token_compiler.compile_and_validate(
                added_tokens, llm_client, revalidate=revalidate
            )

    def create_ni_document(
        self,
        initial_content: str,
        version: str = "v1",
    ) -> Any:
        """Create a new NI document with initial content.

        Args:
            initial_content: Initial content for the document
            version: Document version

        Returns:
            Created document domain object
        """
        # Parse initial content
        model = ModelFactory.get_model(ClientType.OPENAI, OpenAIModelType.GPT_4O_MINI)
        llm_client = OpenAILLMClient(model)

        # Parse content into token data
        parsed_data = self.llm_parser.parse_document(initial_content)
        token_data = self._flatten_llm_output(parsed_data)

        # Create document
        doc = self.doc_repo.create_document(initial_content, version)

        # Create initial tokens
        tokens = self.document_updater.create_tokens(doc.id, initial_content, token_data)

        # Commit to ensure tokens are in DB before compilation
        if isinstance(self.doc_repo, DocumentRepository):
            cast(DocumentRepository, self.doc_repo).session.commit()

        # Compile tokens
        if tokens:
            self.token_compiler.compile_and_validate(tokens, llm_client, revalidate=True)

        return doc
