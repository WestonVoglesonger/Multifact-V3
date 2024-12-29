"""Service for orchestrating the NI-to-code workflow."""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from snc.domain.models import DomainToken, DomainDocument
from snc.application.interfaces.icode_fixer_service import ICodeFixerService
from snc.application.interfaces.idocument_repository import IDocumentRepository
from snc.application.interfaces.itoken_repository import ITokenRepository
from snc.application.services.token_compiler import TokenCompiler
from snc.application.services.document_updater import DocumentUpdater
from snc.application.services.token_diff_service import TokenDiffService
from snc.application.services.exceptions import (
    DocumentNotFoundError,
    LLMParsingError,
    ArtifactNotFoundError,
    TokenNotFoundError,
)
from snc.infrastructure.llm.llm_service_impl import ConcreteLLMService
from snc.infrastructure.llm.model_factory import (
    GroqModelType,
    OpenAIModelType,
    ClientType,
    ModelFactory,
)
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository
from snc.infrastructure.llm.base_llm_client import BaseLLMClient
from snc.infrastructure.llm.groq_llm_client import GroqLLMClient
from snc.infrastructure.llm.openai_llm_client import OpenAILLMClient


class NIOrchestrator:
    """Service for orchestrating the NI-to-code workflow.

    Handles the full workflow from NI document to code:
    - Creating and updating NI documents
    - Parsing and diffing document content
    - Compiling tokens to code
    - Validating and fixing code if needed
    - Managing artifacts and error details
    """

    def __init__(
        self,
        doc_repo: IDocumentRepository,
        token_repo: ITokenRepository,
        artifact_repo: ArtifactRepository,
        llm_parser: ConcreteLLMService,
        token_diff_service: TokenDiffService,
        document_updater: DocumentUpdater,
        token_compiler: TokenCompiler,
        code_fixer_service: Optional[ICodeFixerService] = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            doc_repo: Repository for document operations
            token_repo: Repository for token operations
            artifact_repo: Repository for artifact operations
            llm_parser: Service for parsing NI with LLM
            token_diff_service: Service for diffing tokens
            document_updater: Service for updating documents
            token_compiler: Service for compiling tokens
            code_fixer_service: Optional service for fixing invalid code
        """
        self.doc_repo = doc_repo
        self.token_repo = token_repo
        self.artifact_repo = artifact_repo
        self.llm_parser = llm_parser
        self.token_diff_service = token_diff_service
        self.document_updater = document_updater
        self.token_compiler = token_compiler
        self.code_fixer_service = code_fixer_service
        self.logger = logging.getLogger(__name__)

    def create_ni_document(
        self,
        initial_content: str,
        version: str = "v1",
    ) -> DomainDocument:
        """Create and persist a new NI document.

        Args:
            initial_content: Initial document content
            version: Document version string

        Returns:
            Newly created domain document

        Raises:
            DocumentNotFoundError: If document creation fails
            LLMParsingError: If content parsing fails
        """
        new_doc = DomainDocument(
            doc_id=0,  # 0 => means not yet in DB
            content=initial_content,
            version=version,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        # The doc_repo internally saves and re-queries
        saved_doc = self.doc_repo.save_document(new_doc)
        if not saved_doc:
            raise DocumentNotFoundError("Failed to create new document")

        # Parse the content, flatten it, and add tokens to DB
        parsed_doc = self.llm_parser.parse_document(initial_content)
        flattened_doc = self._flatten_llm_output(parsed_doc)
        self.token_repo.add_new_tokens(saved_doc.id, flattened_doc)

        if not saved_doc:
            raise DocumentNotFoundError("Failed to create new document")
        self.logger.info(
            "Created new NI document id=%d, version=%s", saved_doc.id, version
        )
        return saved_doc

    def get_ni_document(self, ni_id: int) -> DomainDocument:
        """Retrieve a document from the repository.

        Args:
            ni_id: Document ID to retrieve

        Returns:
            Retrieved domain document

        Raises:
            DocumentNotFoundError: If document not found
        """
        doc = self.doc_repo.get_document(ni_id)
        if not doc:
            raise DocumentNotFoundError(f"NI document {ni_id} not found.")
        return doc

    def update_ni_and_compile(
        self,
        ni_id: int,
        new_content: str,
        model_type: Union[GroqModelType, OpenAIModelType],
        revalidate: bool = True,
    ) -> None:
        """Update document content and compile affected tokens.

        Args:
            ni_id: Document ID to update
            new_content: New document content
            model_type: LLM model type to use
            revalidate: Whether to validate compiled artifacts

        Raises:
            DocumentNotFoundError: If document not found
            LLMParsingError: If content parsing fails
            CompilationError: If compilation fails
            ValidationError: If validation fails
        """
        # Ensure the doc exists
        self.get_ni_document(ni_id)

        # Parse new content with the LLM
        try:
            structured_data = self.llm_parser.parse_document(new_content)
        except Exception as e:
            self.logger.error("Failed to parse NI %d with LLM: %s", ni_id, e)
            raise LLMParsingError(str(e))

        # Flatten LLM output => data for tokens
        new_tokens_data = self._flatten_llm_output(structured_data)

        # Grab old tokens + diff
        old_tokens = self.token_repo.get_tokens_with_artifacts(ni_id)
        diff_result = self.token_diff_service.diff_tokens(old_tokens, new_tokens_data)

        # Update DB: doc content + tokens changes
        newly_added_tokens = self.document_updater.apply_diff(
            ni_id, new_content, diff_result
        )

        # Compile changed + newly added
        changed_tokens = [c[0] for c in diff_result.changed]
        tokens_to_compile = changed_tokens + newly_added_tokens
        self.token_compiler.compile_and_validate(
            tokens_to_compile, self._get_llm_client(model_type), revalidate
        )

        self.logger.info(
            "NI doc %d updated. Compiled %d tokens.", ni_id, len(tokens_to_compile)
        )

    def compile_tokens(
        self,
        tokens: List[DomainToken],
        model_type: Union[GroqModelType, OpenAIModelType],
    ) -> None:
        """Compile and validate a list of tokens.

        Args:
            tokens: List of tokens to compile
            model_type: LLM model type to use

        Raises:
            CompilationError: If compilation fails
            ValidationError: If validation fails
        """
        self.token_compiler.compile_and_validate(
            tokens, self._get_llm_client(model_type), revalidate=True
        )

    def fix_artifact_code(self, artifact_id: int, max_attempts: int = 2) -> bool:
        """Try to fix invalid artifact code.

        Args:
            artifact_id: ID of artifact to fix
            max_attempts: Maximum number of fix attempts

        Returns:
            True if artifact is valid after fixes, False otherwise

        Raises:
            RuntimeError: If no code fixer service configured
            ArtifactNotFoundError: If artifact not found
        """
        if not self.code_fixer_service:
            raise RuntimeError(
                "No ICodeFixerService provided; cannot fix code automatically."
            )

        artifact = self.artifact_repo.get_artifact_by_id(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"Artifact {artifact_id} not found.")

        for attempt in range(max_attempts):
            result = self.token_compiler.validation_service.validate_artifact(
                artifact_id
            )
            if result.success:
                return True
            # If not success, fix code with code_fixer
            error_summary = self._summarize_errors(result.errors)
            new_code = self.code_fixer_service.fix_code(artifact.code, error_summary)

            # Update artifact code in DB (mark valid=False until next check)
            self.artifact_repo.update_artifact_code(artifact_id, new_code, valid=False)
            self.logger.info(
                "Fixed code attempt %d, artifact %d", attempt + 1, artifact_id
            )

        # final check
        final_result = self.token_compiler.validation_service.validate_artifact(
            artifact_id
        )
        if final_result.success:
            return True
        else:
            self.logger.warning(
                "Artifact %d still invalid after %d attempts.",
                artifact_id,
                max_attempts,
            )
            return False

    def get_artifact_info(self, artifact_id: int) -> Dict[str, Any]:
        """Get detailed information about an artifact.

        Args:
            artifact_id: ID of artifact to get info for

        Returns:
            Dictionary containing:
                - code: The artifact's code
                - valid: Whether the code is valid
                - errors: Any validation errors
                - doc_content: Associated document content
                - token_content: Associated token content

        Raises:
            ArtifactNotFoundError: If artifact not found
        """
        artifact = self.artifact_repo.get_artifact_by_id(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"Artifact {artifact_id} not found.")

        # Validate to retrieve error info
        result = self.token_compiler.validation_service.validate_artifact(artifact_id)
        token = self.token_repo.get_token_by_id(artifact.ni_token_id)
        if not token:
            raise TokenNotFoundError(f"Token for artifact {artifact_id} not found.")

        doc_id = self._find_doc_id_for_token(token)
        ni_doc = self.doc_repo.get_document(doc_id)
        if not ni_doc:
            raise DocumentNotFoundError(
                f"NI doc for token {token.token_uuid} not found."
            )

        return {
            "artifact_id": artifact_id,
            "code": artifact.code,
            "valid": artifact.valid,
            "errors": [e.__dict__ for e in result.errors],
            "ni_content": ni_doc.content,
            "token_content": token.content,
            "doc_id": doc_id,
        }

    def list_tokens_with_artifacts(self, ni_id: int) -> List[Dict[str, Any]]:
        """Get all tokens and artifacts for a document.

        Args:
            ni_id: Document ID to get tokens for

        Returns:
            List of dictionaries containing token and artifact info
        """
        tokens_with_arts = self.token_repo.get_tokens_with_artifacts(ni_id)
        result = []
        for token, artifact in tokens_with_arts:
            info = {
                "token_id": token.id,
                "token_type": token.token_type,
                "token_name": token.token_name,
                "artifact_id": artifact.id if artifact else None,
                "valid": artifact.valid if artifact else None,
                "code": artifact.code if artifact else None,
            }
            result.append(info)
        return result

    #
    # ------------------ 5) Internals --------------------
    #
    def _find_doc_id_for_token(self, token: DomainToken) -> int:
        doc_id = self.token_repo.get_doc_id_for_token_uuid(token.token_uuid)
        if doc_id is None:
            raise DocumentNotFoundError(
                f"No document found for token {token.token_uuid}"
            )
        return doc_id

    def _flatten_llm_output(self, data: dict) -> List[dict]:
        """Convert hierarchical LLM output into a flat list of tokens.

        Takes the parsed JSON from LLM that looks like:
        {
        "scenes": [
            {
            "name": "...",
            "narrative": "...",
            "functions": [ { "name": "...", ... }, ... ],
            "components": [ ... ]
            },
            ...
        ]
        }
        and returns a flat list of token dicts, e.g.:
        [
        {"type": "scene", "scene_name": "...", "content": "..."},
        {"type": "function", "function_name": "...", "content": "..."},
        {"type": "component", "component_name": "...", "content": "..."},
        ...
        ]
        """
        import hashlib

        result = []
        for scene in data.get("scenes", []):
            scene_name = scene.get("name", "UnnamedScene")
            scene_narrative = scene.get("narrative", "")

            # 1) Scene token
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

            # 2) Functions
            for func in scene.get("functions", []):
                func_name = func.get("name")
                func_narrative = func.get("narrative", "")
                if not func_name or not func_name.strip():
                    func_name = "func_" + hashlib.sha256().hexdigest()[:8]

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

            # 3) Components
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

                # 4) Component functions
                for func in comp.get("functions", []):
                    func_name = func.get("name")
                    func_narrative = func.get("narrative", "")
                    if not func_name or not func_name.strip():
                        func_name = "func_" + hashlib.sha256().hexdigest()[:8]

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

        return result

    def _get_llm_client(
        self, model_type: GroqModelType | OpenAIModelType
    ) -> BaseLLMClient:
        """Get an LLM client for the given model type."""
        model = ModelFactory.get_model(
            (
                ClientType.GROQ
                if isinstance(model_type, GroqModelType)
                else ClientType.OPENAI
            ),
            model_type,
        )
        if isinstance(model_type, GroqModelType):
            return GroqLLMClient(model)
        else:
            return OpenAILLMClient(model)

    def _summarize_errors(self, errors: List[Any]) -> str:
        """Turn a list of ValidationErrors into a text summary."""
        lines = ["Found these errors:"]
        for e in errors:
            lines.append(f"{e.file}({e.line},{e.char}): {e.message}")
        return "\n".join(lines)
