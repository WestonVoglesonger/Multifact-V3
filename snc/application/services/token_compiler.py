"""Service for compiling tokens into code artifacts."""

import logging
import hashlib
import concurrent.futures
from typing import List, Dict, Set, Any, Optional, Callable
from collections import defaultdict
from sqlalchemy.orm import Session, sessionmaker, scoped_session

from snc.domain.models import DomainToken
from snc.infrastructure.llm.base_llm_client import BaseLLMClient
from snc.application.interfaces.icompilation_service import ICompilationService
from snc.application.interfaces.ivalidation_service import IValidationService
from snc.application.interfaces.icode_evaluation_service import ICodeEvaluationService
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.infrastructure.entities.ni_token import NIToken
from snc.database import engine


class TokenCompiler:
    """Service for compiling tokens into code artifacts.

    Handles the compilation of tokens into code artifacts, including:
    - Parallel compilation of independent tokens
    - Validation of compiled artifacts
    - Code evaluation and scoring
    - Session management for thread safety
    """

    def __init__(
        self,
        compilation_service: ICompilationService,
        validation_service: IValidationService,
        evaluation_service: ICodeEvaluationService,
        session_factory: Optional[Callable[[], Session]] = None,
    ):
        """Initialize the compiler.

        Args:
            compilation_service: Service for compiling tokens
            validation_service: Service for validating artifacts
            evaluation_service: Service for evaluating code
            session_factory: Optional factory function to create new sessions
        """
        self.compilation_service = compilation_service
        self.validation_service = validation_service
        self.evaluation_service = evaluation_service
        self.session_factory = session_factory
        self.logger = logging.getLogger(__name__)

    def _group_tokens_by_level(self, tokens: List[DomainToken]) -> List[List[DomainToken]]:
        """Group tokens by their dependency level.

        Tokens in the same level can be compiled in parallel since they
        have no dependencies on each other.

        Args:
            tokens: List of tokens to group

        Returns:
            List of token groups, where each group can be compiled in parallel
        """
        # Build dependency graph
        graph: Dict[int, Set[int]] = defaultdict(set)
        for token in tokens:
            if token.id is not None:
                for dep in token.dependencies:
                    if dep.id is not None:
                        graph[token.id].add(dep.id)

        # Find tokens with no dependencies
        all_ids = {t.id for t in tokens if t.id is not None}
        dependent_ids = set().union(*graph.values())
        roots = all_ids - dependent_ids

        # Group tokens by level
        levels: List[List[DomainToken]] = []
        processed: Set[Any] = set()
        current_level = [t for t in tokens if t.id in roots]

        while current_level:
            levels.append(current_level)
            processed.update(t.id for t in current_level if t.id is not None)

            # Find next level (tokens whose dependencies are all processed)
            next_level = []
            for token in tokens:
                if token.id is not None and token.id not in processed:
                    deps = graph[token.id]
                    if all(dep in processed for dep in deps):
                        next_level.append(token)
            current_level = next_level

        return levels

    def _generate_hash(self, content: str) -> str:
        """Generate a hash for the token content.

        Args:
            content: Content to hash

        Returns:
            SHA-256 hash of the content
        """
        return hashlib.sha256(content.encode()).hexdigest()

    def _copy_token_to_session(self, token: DomainToken, session: Session) -> None:
        """Copy a token to a thread-local session.

        Args:
            token: Token to copy
            session: Thread-local session
        """
        try:
            # Get the original token to access relationships
            original_token = (
                session.query(NIToken).filter(NIToken.token_uuid == token.token_uuid).one_or_none()
            )

            if original_token:
                # If we found the original token, use its document ID
                new_token = NIToken(
                    id=original_token.id,  # Use original token's ID
                    ni_document_id=original_token.ni_document_id,
                    token_uuid=token.token_uuid,
                    token_name=token.token_name,
                    token_type=token.token_type,
                    scene_name=token.scene_name,
                    component_name=token.component_name,
                    function_name=token.function_name,
                    content=token.content,
                    hash=self._generate_hash(token.content),
                )
                # Instead of merge, expire the original and update its values
                session.expire(original_token)
                for attr, value in new_token.__dict__.items():
                    if not attr.startswith("_"):
                        setattr(original_token, attr, value)
            else:
                raise ValueError(f"Token {token.token_uuid} not found in database")

        except Exception as e:
            self.logger.error("Failed to copy token %s: %s", token.token_uuid, str(e))
            raise

    def _compile_token_wrapper(
        self,
        token: DomainToken,
        llm_client: BaseLLMClient,
        revalidate: bool,
        session: Optional[Session] = None,
    ) -> None:
        """Process a single token for compilation.

        Used for parallel processing, handles session management and cleanup.

        Args:
            token: Token to compile
            llm_client: LLM client to use for compilation
            revalidate: Whether to validate the compiled artifact
            session: Optional database session to use

        Raises:
            ValueError: If token ID is None
        """
        if token.id is None:
            self.logger.error("Cannot compile token with None ID")
            raise ValueError("Token ID cannot be None")

        try:
            self.logger.debug("Starting compilation of token %d", token.id)

            if not session:
                raise ValueError("Session is required for token compilation")

            # Copy token to this session
            self._copy_token_to_session(token, session)
            self.logger.debug("Token %d copied to thread-local session", token.id)

            # Set thread-local session in services
            setattr(self.compilation_service, "session", session)
            setattr(self.validation_service, "session", session)

            # Initial compilation
            self.logger.info("Compiling token %d (%s)", token.id, token.token_type)
            artifact = getattr(self.compilation_service, "compile_token")(token.id, llm_client)
            if not artifact:
                self.logger.error("Failed to compile token %d", token.id)
                return

            # Commit to ensure artifact exists in DB
            session.commit()

            # Validate if requested
            if revalidate and artifact.id is not None:
                self.logger.debug("Validating artifact %d", artifact.id)
                validation_result = self.validation_service.validate_artifact(artifact.id)
                if not validation_result.success:
                    error_messages = "; ".join(error.message for error in validation_result.errors)
                    self.logger.warning(
                        "Artifact %d validation failed: %s", artifact.id, error_messages
                    )
                    artifact.valid = False
                    getattr(self.compilation_service, "update_artifact")(artifact)

            # Evaluate all artifacts, regardless of validation status
            if artifact.id is not None:
                self.logger.debug("Evaluating artifact %d", artifact.id)
                evaluation_result = self.evaluation_service.evaluate_code(
                    artifact.code,
                    {"token_id": token.id, "artifact_id": artifact.id},
                )
                artifact.score = evaluation_result.get("score", 0)
                artifact.feedback = evaluation_result.get("feedback", "")
                getattr(self.compilation_service, "update_artifact")(artifact)

            # Final commit
            session.commit()

        except Exception as e:
            self.logger.error("Failed to compile token %s: %s", token.token_uuid, str(e))
            if session:
                session.rollback()
            raise
        finally:
            if session:
                session.close()

    def compile_and_validate(
        self,
        tokens: List[DomainToken],
        llm_client: BaseLLMClient,
        revalidate: bool = True,
    ) -> None:
        """Compile and validate a list of tokens.

        Tokens are grouped by dependency level and compiled in parallel
        within each level.

        Args:
            tokens: List of tokens to compile
            llm_client: LLM client to use for compilation
            revalidate: Whether to validate compiled artifacts
        """
        if not tokens:
            self.logger.info("No tokens to compile")
            return

        # Group tokens by dependency level
        token_levels = self._group_tokens_by_level(tokens)
        self.logger.info("Grouped %d tokens into %d levels", len(tokens), len(token_levels))

        # Process each level in sequence
        for level_idx, level_tokens in enumerate(token_levels):
            self.logger.info("Processing level %d with %d tokens", level_idx, len(level_tokens))

            # Process tokens in this level in parallel
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for token in level_tokens:
                    # Create a new session for each token
                    if self.session_factory:
                        session = self.session_factory()
                        futures.append(
                            executor.submit(
                                self._compile_token_wrapper,
                                token,
                                llm_client,
                                revalidate,
                                session,
                            )
                        )
                    else:
                        self.logger.error("No session factory available")
                        raise ValueError("Session factory is required for parallel compilation")

                # Wait for all futures to complete
                for future in futures:
                    try:
                        future.result()  # This will raise any exceptions that occurred
                    except Exception as e:
                        self.logger.error("Token compilation failed: %s", e)
                        raise
