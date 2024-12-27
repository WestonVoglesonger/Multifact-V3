import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.domain.models import DomainToken, DomainDocument
from backend.application.services.token_diff_service import TokenDiffService
from backend.application.services.document_updater import DocumentUpdater
from backend.application.services.token_compiler import TokenCompiler
from backend.application.services.tokenization_service import TokenizationService
from backend.application.services.exceptions import (
    DocumentNotFoundError,
    ArtifactNotFoundError,
    TokenNotFoundError,
    LLMParsingError,
)
from backend.application.interfaces.idocument_repository import IDocumentRepository
from backend.application.interfaces.itoken_repository import ITokenRepository
from backend.infrastructure.llm.llm_service_impl import ConcreteLLMService
from backend.infrastructure.llm.model_factory import GroqModelType, OpenAIModelType
from backend.infrastructure.llm.client_factory import ClientFactory
from backend.infrastructure.llm.groq_llm_client import GroqLLMClient
from backend.infrastructure.llm.openai_llm_client import OpenAILLMClient
from backend.infrastructure.repositories.artifact_repository import ArtifactRepository
from backend.application.interfaces.icode_fixer_service import ICodeFixerService


class NIOrchestrator:
    """
    Orchestrates the full NI-to-code workflow:
      - Create new NI docs
      - Update them with new content
      - Parse/diff/compile
      - Optionally handle code fixes if validation fails
      - Retrieve artifacts or error details
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
    ):
        self.doc_repo = doc_repo
        self.token_repo = token_repo
        self.artifact_repo = artifact_repo
        self.llm_parser = llm_parser
        self.token_diff_service = token_diff_service
        self.document_updater = document_updater
        self.token_compiler = token_compiler
        self.code_fixer_service = code_fixer_service  # optional
        self.logger = logging.getLogger(__name__)

    #
    # ------------------ 1) Creation / Basic Methods --------------------
    #
    def create_ni_document(
        self,
        initial_content: str,
        version: str = "v1",
    ) -> DomainDocument:
        """
        Creates and persists a new NI document with `initial_content`.
        Returns the newly created DomainDocument. 
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

        # 2) Parse the content, flattent it, and add tokens to DB
        parsed_doc = self.llm_parser.parse_document(initial_content)
        flattened_doc = self._flatten_llm_output(parsed_doc)
        self.token_repo.add_new_tokens(saved_doc.id, flattened_doc)

        if not saved_doc:
            raise DocumentNotFoundError("Failed to create new document")
        self.logger.info(
            f"Created new NI document id={saved_doc.id}, version={version}"
        )
        return saved_doc

    def get_ni_document(self, ni_id: int) -> DomainDocument:
        """
        Retrieve a DomainDocument from the repository by ID.
        Raises DocumentNotFoundError if not found.
        """
        doc = self.doc_repo.get_document(ni_id)
        if not doc:
            raise DocumentNotFoundError(f"NI document {ni_id} not found.")
        return doc

    #
    # ------------------ 2) Update + Compile Workflow --------------------
    #
    def update_ni_and_compile(
        self,
        ni_id: int,
        new_content: str,
        model_type: GroqModelType | OpenAIModelType,
        revalidate: bool = True,
    ) -> None:
        """
        Replaces the existing doc’s content with `new_content` and compiles.
        - LLM is used to parse the new content
        - The diff is applied (update / remove / add tokens)
        - The newly changed or added tokens are compiled
        - If revalidate=True, each compiled artifact is validated

        Raises:
          - DocumentNotFoundError if doc doesn’t exist
          - LLMParsingError if LLM parse fails
          - etc.
        """
        # 1) Ensure the doc exists
        ni_doc = self.get_ni_document(ni_id)

        # 2) Parse new content with the LLM
        try:
            structured_data = self.llm_parser.parse_document(new_content)
        except Exception as e:
            self.logger.error(f"Failed to parse NI {ni_id} with LLM: {e}")
            raise LLMParsingError(str(e))

        # 3) Flatten LLM output => data for tokens
        new_tokens_data = self._flatten_llm_output(structured_data)

        # 4) Grab old tokens + diff
        old_tokens = self.token_repo.get_tokens_with_artifacts(ni_id)
        diff_result = self.token_diff_service.diff_tokens(old_tokens, new_tokens_data)

        # 5) Update DB: doc content + tokens changes
        newly_added_tokens = self.document_updater.apply_diff(
            ni_id, new_content, diff_result
        )

        # 6) Compile changed + newly added
        changed_tokens = [c[0] for c in diff_result.changed]
        tokens_to_compile = changed_tokens + newly_added_tokens
        self.token_compiler.compile_and_validate(
            tokens_to_compile, self._get_llm_client(model_type), revalidate
        )

        self.logger.info(
            f"NI doc {ni_id} updated with new content. "
            f"Compiled {len(tokens_to_compile)} changed/new tokens."
        )

    def compile_tokens(self, tokens: List[DomainToken], model_type: GroqModelType | OpenAIModelType) -> None:
        """
        Compiles a list of tokens and validates them.
        """
        self.token_compiler.compile_and_validate(tokens, self._get_llm_client(model_type), revalidate=True)

    #
    # ------------------ 3) Handling Validation Errors (Optional) --------------------
    #
    def fix_artifact_code(self, artifact_id: int, max_attempts: int = 2) -> bool:
        """
        If code_fixer_service is configured, tries to fix an artifact’s code
        if it fails validation. This is an optional step if you want automated
        code repair.

        Returns True if the artifact is valid after fix attempts, else False.
        Raises if artifact doesn’t exist or no code_fixer_service is present.
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
            self.logger.info(f"Fixed code attempt {attempt+1}, artifact {artifact_id}")

        # final check
        final_result = self.token_compiler.validation_service.validate_artifact(
            artifact_id
        )
        if final_result.success:
            return True
        else:
            self.logger.warning(
                f"Artifact {artifact_id} still invalid after {max_attempts} fix attempts."
            )
            return False

    #
    # ------------------ 4) Retrieve Info About Artifacts, Tokens, Etc. --------------------
    #
    def get_artifact_info(self, artifact_id: int) -> Dict[str, Any]:
        """
        Return detailed info about an artifact:
         - code
         - validity
         - errors if any
         - associated NI doc content
         - associated token content
        """
        artifact = self.artifact_repo.get_artifact_by_id(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"Artifact {artifact_id} not found.")

        # Validate to retrieve error info (the method might re-validate each time,
        # or you can store errors from the last check)
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

    def list_tokens_with_artifacts(self, doc_id: int) -> List[Dict[str, Any]]:
        """
        Return a list of tokens and their compiled artifacts for a given doc.
        """
        tokens_with_artifacts = self.token_repo.get_tokens_with_artifacts(doc_id)
        result = []
        for t, a in tokens_with_artifacts:
            entry = {
                "token_id": t.id,
                "token_type": t.token_type,
                "content": t.content,
                "artifact_id": a.id if a else None,
                "valid": a.valid if a else None,
                "code": a.code if a else None,
            }
            result.append(entry)
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
        return self._default_flatten_llm_output(data)

    def _default_flatten_llm_output(self, data: dict) -> List[dict]:
        """
        Takes the parsed JSON from LLM that looks like:
        {
          "scenes": [
            {
              "name": "MainScene",
              "narrative": "...",
              "components": [
                {
                  "name": "SomeComp",
                  "narrative": "...",
                  "functions": [ { "name": "...", "narrative": "..." }, ... ]
                },
                ...
              ]
            },
            ...
          ]
        }

        and returns a flat list of token dicts, e.g.:
        [
          {"type": "scene", "scene_name": "MainScene", "content": "..."},
          {"type": "component", "component_name": "SomeComp", "content": "..."},
          {"type": "function", "function_name": "...", "content": "..."}
        ]
        """
        result = []
        for scene in data.get("scenes", []):
            scene_name = scene.get("name", "UnnamedScene")
            scene_narrative = scene.get("narrative", "")
            result.append(
                {
                    "type": "scene",
                    "scene_name": scene_name,
                    "component_name": None,
                    "content": scene_narrative,
                }
            )

            for comp in scene.get("components", []):
                comp_name = comp.get("name", "UnnamedComponent")
                comp_narrative = comp.get("narrative", "")
                result.append(
                    {
                        "type": "component",
                        "scene_name": None,
                        "component_name": comp_name,
                        "content": comp_narrative,
                    }
                )

                for func in comp.get("functions", []):
                    func_name = func.get("name")
                    func_narrative = func.get("narrative", "")
                    if not func_name or not func_name.strip():
                        func_name = (
                            "func_"
                            + hashlib.sha256().hexdigest()[:8]
                        )
                    result.append(
                        {
                            "type": "function",
                            "scene_name": None,
                            "component_name": None,
                            "function_name": func_name,
                            "content": func_narrative,
                        }
                    )
        return result

    def _get_llm_client(
        self, model_type: GroqModelType | OpenAIModelType
    ) -> GroqLLMClient | OpenAILLMClient:
        return ClientFactory.get_llm_client(model_type)

    def _summarize_errors(self, errors: List[Any]) -> str:
        """
        Turn a list of ValidationErrors into a text summary
        that can be used as 'error_summary' for fix_code calls.
        """
        lines = ["Found these errors:"]
        for e in errors:
            lines.append(f"{e.file}({e.line},{e.char}): {e.message}")
        return "\n".join(lines)
