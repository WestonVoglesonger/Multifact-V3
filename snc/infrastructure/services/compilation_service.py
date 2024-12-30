"""Service for compiling narrative tokens into artifacts."""

from typing import Dict, Any, List, cast, Optional
from sqlalchemy.orm import Session
import re
import threading
import logging
from datetime import datetime, timezone

from snc.domain.models import DomainDocument, DomainCompiledMultifact
from snc.domain.model_types import CompilationResult
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.application.interfaces.icompilation_service import ICompilationService
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.application.interfaces.illm_client import ILLMClient


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
            return CompilationResult(
                code=code,
                valid=True,
                errors=None,
                cache_hit=False,
                score=0.95,  # Default score for direct compilation
                feedback="Compiled successfully",
            )
        except Exception as e:
            return CompilationResult(
                code="",
                valid=False,
                errors=[str(e)],
                cache_hit=False,
                score=0.0,
                feedback=str(e),
            )

    def compile_token(
        self,
        token_id: int,
        llm_client: ILLMClient,
    ) -> Optional[DomainCompiledMultifact]:
        """Compile a single token into code.

        Args:
            token_id: ID of token to compile
            llm_client: LLM client to use for code generation

        Returns:
            Compiled artifact if successful, None otherwise
        """
        try:
            # Get token
            token = self.session.query(NIToken).get(token_id)
            if not token:
                raise ValueError(f"Token with id {token_id} not found")

            # Check for existing valid artifact with matching hash
            existing_artifact = (
                self.session.query(CompiledMultifact)
                .filter(
                    CompiledMultifact.ni_token_id == token_id,
                    CompiledMultifact.token_hash == token.hash,
                    CompiledMultifact.valid == True,
                )
                .order_by(CompiledMultifact.created_at.desc())
                .first()
            )

            if existing_artifact is not None:
                # Return existing artifact
                return existing_artifact.to_domain_artifact()

            # Generate new code
            generated_code = llm_client.generate_code(token.content)

            # Create new artifact
            new_artifact = CompiledMultifact(
                ni_token_id=token_id,
                language="typescript",
                framework="angular",
                code=generated_code,
                valid=True,
                cache_hit=False,
                token_hash=token.hash,
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(new_artifact)
            self.session.flush()  # Get the ID without committing

            # Convert to domain artifact
            domain_artifact = new_artifact.to_domain_artifact()

            # Commit the transaction
            self.session.commit()

            return domain_artifact

        except Exception as e:
            self.logger.error(f"Failed to compile token {token_id}: {e}")
            self.session.rollback()
            raise

    def compile_document(
        self, document: DomainDocument, llm_client: ILLMClient
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

            # Compile token
            artifact_domain = self.compile_token(tok.id, llm_client)
            if artifact_domain is None or artifact_domain.id is None:
                self.logger.error(f"Failed to compile token {tok.id}")
                continue

            # Get entity artifact
            artifact_ent = self.session.query(CompiledMultifact).get(artifact_domain.id)
            if artifact_ent:
                compiled_artifacts.append(cast(CompiledMultifact, artifact_ent))

        return compiled_artifacts

    def compile_token_with_dependencies(
        self, token_id: int, llm_client: ILLMClient
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
        if domain_artifact is None or domain_artifact.id is None:
            self.logger.error(f"Failed to compile token {result.id}")
            return compiled_artifacts

        # Get entity artifact
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
