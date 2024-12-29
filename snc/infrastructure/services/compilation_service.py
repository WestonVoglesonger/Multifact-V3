"""Service for compiling narrative tokens into artifacts."""

from typing import Dict, Any, List, cast
from sqlalchemy.orm import Session
import re
import threading
import logging

from snc.domain.models import DomainDocument, DomainCompiledMultifact, DomainMultifact
from snc.domain.model_types import CompilationResult
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.llm.base_llm_client import BaseLLMClient
from snc.application.interfaces.icompilation_service import ICompilationService
from snc.application.services.code_evaluation_service import CodeEvaluationService


class ConcreteCompilationService(ICompilationService):
    """Service for compiling narrative tokens into artifacts.

    This service handles the compilation of tokens into their corresponding
    artifacts, managing dependencies, caching, and evaluation.
    """

    def __init__(self, session: Session):
        """Initialize the compilation service.

        Args:
            session: Database session to use
        """
        self._main_session = session
        self._thread_local = threading.local()
        self._thread_local.session = session
        self.logger = logging.getLogger(__name__)

    @property
    def session(self) -> Session:
        """Get the current thread's database session."""
        return self._thread_local.session

    @session.setter
    def session(self, new_session: Session) -> None:
        """Set the current thread's database session.

        Args:
            new_session: New session to use
        """
        self._thread_local.session = new_session

    def compile(self, code: str) -> CompilationResult:
        """Compile code and return the result.

        Args:
            code: Code to compile

        Returns:
            Compilation result with status and errors if any
        """
        try:
            return CompilationResult(code=code, valid=True, errors=None, cache_hit=False)
        except Exception as e:
            return CompilationResult(code="", valid=False, errors=[str(e)], cache_hit=False)

    def compile_multifact(self, multifact: DomainMultifact) -> DomainCompiledMultifact:
        """Compile a multifact into a compiled multifact."""
        if multifact.is_compiled is True:
            return DomainCompiledMultifact(
                id=multifact.id,
                name=multifact.name,
                description=multifact.description,
                code=multifact.code,
                metadata=multifact.metadata,
                is_compiled=True,
                created_at=multifact.created_at,
                updated_at=multifact.updated_at,
                compiled_at=multifact.compiled_at,
                version=multifact.version,
                parent_id=multifact.parent_id,
                parent_version=multifact.parent_version,
                parent_type=multifact.parent_type,
                parent_name=multifact.parent_name,
                parent_description=multifact.parent_description,
                parent_metadata=multifact.parent_metadata,
                parent_created_at=multifact.parent_created_at,
                parent_updated_at=multifact.parent_updated_at,
                parent_compiled_at=multifact.parent_compiled_at,
                parent_is_compiled=multifact.parent_is_compiled,
                parent_code=multifact.parent_code,
                parent_version_id=multifact.parent_version_id,
                parent_version_name=multifact.parent_version_name,
                parent_version_description=multifact.parent_version_description,
                parent_version_metadata=multifact.parent_version_metadata,
                parent_version_created_at=multifact.parent_version_created_at,
                parent_version_updated_at=multifact.parent_version_updated_at,
                parent_version_compiled_at=multifact.parent_version_compiled_at,
                parent_version_is_compiled=multifact.parent_version_is_compiled,
                parent_version_code=multifact.parent_version_code,
            )

    def compile_token(self, token_id: int, llm_client: BaseLLMClient) -> DomainCompiledMultifact:
        """Compile a token into a multifact.

        Args:
            token_id: ID of token to compile
            llm_client: LLM client to use for code generation

        Returns:
            Compiled artifact

        Raises:
            ValueError: If token not found or invalid
        """
        try:
            # Check for cached artifacts
            cached_artifact = (
                self._thread_local.session.query(CompiledMultifact)
                .filter(
                    CompiledMultifact.ni_token_id == token_id,
                    CompiledMultifact.cache_hit == True,
                )
                .first()
            )
            if cached_artifact:
                return cached_artifact.to_domain_artifact()

            # Get token
            token = (
                self._thread_local.session.query(NIToken)
                .filter(NIToken.id == token_id)
                .one_or_none()
            )
            if not token:
                raise ValueError(f"Token with id {token_id} not found")

            # Extract target name from token content
            patterns = {
                "scene": r"\[Scene:(\w+)\]",
                "component": r"\[Component:(\w+)\]",
                "service": r"\[Service:(\w+)\]",
                "interface": r"\[Interface:(\w+)\]",
                "type": r"\[Type:(\w+)\]",
                "function": r"\[Function:(\w+)\]",
            }

            pattern = patterns.get(token.token_type)
            if not pattern:
                raise ValueError(f"Unknown token type: {token.token_type}")

            # If content doesn't start with the token type header, add it
            if not token.content.strip().startswith(f"[{token.token_type.title()}:"):
                token.content = f"[{token.token_type.title()}:{token.token_name}]\n{token.content}"

            # Generate code using LLM
            code = llm_client.generate_code(token.content)
            if not code:
                raise ValueError("Failed to generate code")

            # Create new artifact
            artifact = CompiledMultifact(
                ni_token_id=token_id,
                language="typescript",  # Default to TypeScript since we're generating Angular code
                framework="angular",  # Default to Angular framework
                code=code,
                valid=True,
                cache_hit=False,
            )
            self._thread_local.session.add(artifact)
            return artifact.to_domain_artifact()

        except Exception as e:
            self.logger.error(f"Failed to compile token {token_id}: {e}")
            raise

    def compile_document(
        self, document: DomainDocument, llm_client: BaseLLMClient
    ) -> List[CompiledMultifact]:
        """Compile all tokens in a document.

        Args:
            document: Document to compile
            llm_client: LLM client to use for code generation

        Returns:
            List of compiled artifacts

        Raises:
            ValueError: If any token has no ID
        """
        compiled_artifacts: List[CompiledMultifact] = []
        for tok in document.tokens:
            if tok.id is None:
                raise ValueError(f"Token with id {tok.id} not found")
            artifact_domain = self.compile_token(tok.id, llm_client)
            artifact_ent = self.session.query(CompiledMultifact).get(artifact_domain.id)
            if artifact_ent:
                compiled_artifacts.append(cast(CompiledMultifact, artifact_ent))
        return compiled_artifacts

    def compile_token_with_dependencies(
        self, token_id: int, llm_client: BaseLLMClient
    ) -> List[CompiledMultifact]:
        """Compile a token and all its dependencies.

        Args:
            token_id: ID of token to compile
            llm_client: LLM client to use for code generation

        Returns:
            List of compiled artifacts

        Raises:
            ValueError: If token not found
        """
        compiled_artifacts: List[CompiledMultifact] = []
        result = self.session.query(NIToken).get(token_id)
        if not isinstance(result, NIToken):
            raise ValueError(f"Token with id {token_id} not found")

        # Recurse over dependencies:
        for dep_ent in result.dependencies:
            compiled_artifacts_dep = self.compile_token_with_dependencies(dep_ent.id, llm_client)
            compiled_artifacts.extend(compiled_artifacts_dep)

        # Now compile this token:
        domain_artifact = self.compile_token(result.id, llm_client)
        artifact_ent = self.session.query(CompiledMultifact).get(domain_artifact.id)
        if artifact_ent:
            compiled_artifacts.append(cast(CompiledMultifact, artifact_ent))
        return compiled_artifacts

    def mark_artifact_invalid(self, artifact_id: int) -> None:
        """Mark an artifact as invalid.

        Called by TokenCompiler if revalidate fails so the artifact is
        committed with valid=False.

        Args:
            artifact_id: ID of artifact to mark invalid
        """
        artifact_ent = self.session.query(CompiledMultifact).get(artifact_id)
        if artifact_ent:
            artifact_ent.valid = False
            self.session.commit()

    def evaluate_compiled_artifact(
        self, artifact_id: int, evaluator: CodeEvaluationService
    ) -> Dict[str, Any]:
        """Evaluate a compiled artifact using the evaluation service.

        Args:
            artifact_id: ID of artifact to evaluate
            evaluator: Service to use for evaluation

        Returns:
            Evaluation results with score and feedback

        Raises:
            ValueError: If artifact not found
        """
        artifact = self.session.query(CompiledMultifact).get(artifact_id)
        if not artifact:
            raise ValueError(f"Artifact with ID={artifact_id} does not exist.")

        code = artifact.code
        context = {
            "artifact_id": artifact_id,
            "token_id": artifact.ni_token_id,
            "valid": artifact.valid,
        }

        eval_result = evaluator.evaluate_code(code, context)

        # Store the results directly in the artifact
        artifact.score = float(eval_result["score"])
        artifact.feedback = eval_result["feedback"]
        self.session.commit()

        return eval_result

    def update_artifact(self, artifact: DomainCompiledMultifact) -> None:
        """Update an existing artifact.

        Args:
            artifact: Updated artifact data

        Raises:
            Exception: If update fails
        """
        try:
            db_artifact = (
                self._thread_local.session.query(CompiledMultifact)
                .filter(CompiledMultifact.id == artifact.id)
                .one_or_none()
            )
            if db_artifact:
                db_artifact.code = artifact.code
                db_artifact.valid = artifact.valid
                db_artifact.score = artifact.score
                db_artifact.feedback = artifact.feedback
                self._thread_local.session.commit()
        except Exception as e:
            self._thread_local.session.rollback()
            raise e

    def get_session(self) -> Session:
        """Get the current database session.

        Returns:
            Current session
        """
        return self.session
