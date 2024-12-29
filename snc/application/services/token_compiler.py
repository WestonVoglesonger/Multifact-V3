"""Service for compiling tokens into code artifacts."""

import logging
import hashlib
import concurrent.futures
from typing import List, Dict, Set, Any, Optional
from collections import defaultdict
from sqlalchemy.orm import Session, sessionmaker, scoped_session

from snc.domain.models import DomainToken
from snc.infrastructure.llm.base_llm_client import BaseLLMClient
from snc.application.interfaces.icompilation_service import ICompilationService
from snc.application.interfaces.ivalidation_service import IValidationService
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
        evaluation_service: CodeEvaluationService,
        session: Optional[Session] = None,
    ) -> None:
        """Initialize the compiler.

        Args:
            compilation_service: Service for compiling tokens
            validation_service: Service for validating artifacts
            evaluation_service: Service for evaluating code quality
            session: Optional session to use (for testing)
        """
        self.compilation_service = compilation_service
        self.validation_service = validation_service
        self.evaluation_service = evaluation_service
        self.logger = logging.getLogger(__name__)

        # If a session is provided, use it. Otherwise, create a new one for concurrency.
        if session is not None:
            self.Session = lambda: session
        else:
            self.Session = scoped_session(sessionmaker(bind=engine))

    def _get_thread_session(self) -> Session:
        """Get a thread-local session.

        Returns:
            New database session for the current thread
        """
        return self.Session()

    def _group_tokens_by_level(
        self, tokens: List[DomainToken]
    ) -> List[List[DomainToken]]:
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
        # Get the original token to access relationships
        original_token = (
            session.query(NIToken).filter(NIToken.id == token.id).one_or_none()
        )

        if original_token:
            # If we found the original token, use its document ID
            new_token = NIToken(
                id=token.id,
                ni_document_id=original_token.ni_document_id,
                token_uuid=token.token_uuid,
                token_name=token.token_name,
                token_type=token.token_type,
                scene_name=token.scene_name,
                component_name=token.component_name,
                content=token.content,
                hash=self._generate_hash(token.content),
            )
            session.merge(new_token)
            try:
                session.flush()  # Use flush instead of commit to keep transaction open
            except:
                session.rollback()
                raise ValueError(f"Failed to merge token {token.id}")
        else:
            # If token not found, try to refresh the session and try again
            session.expire_all()
            session.commit()  # Commit any pending changes
            session.begin()  # Start a new transaction

            # Try to get the token again
            original_token = (
                session.query(NIToken).filter(NIToken.id == token.id).one_or_none()
            )
            if original_token:
                new_token = NIToken(
                    id=token.id,
                    ni_document_id=original_token.ni_document_id,
                    token_uuid=token.token_uuid,
                    token_name=token.token_name,
                    token_type=token.token_type,
                    scene_name=token.scene_name,
                    component_name=token.component_name,
                    content=token.content,
                    hash=self._generate_hash(token.content),
                )
                session.merge(new_token)
                try:
                    session.flush()  # Use flush instead of commit to keep transaction open
                except:
                    session.rollback()
                    raise ValueError(f"Failed to merge token {token.id}")
            else:
                raise ValueError(f"Token {token.id} not found in database")

    def _compile_token_wrapper(
        self, token: DomainToken, llm_client: BaseLLMClient, revalidate: bool
    ) -> None:
        """Process a single token for compilation.

        Used for parallel processing, handles session management and cleanup.

        Args:
            token: Token to compile
            llm_client: LLM client to use for compilation
            revalidate: Whether to validate the compiled artifact

        Raises:
            ValueError: If token ID is None
        """
        if token.id is None:
            self.logger.error("Cannot compile token with None ID")
            raise ValueError("Token ID cannot be None")

        session = None
        try:
            # Get thread-local session
            session = self._get_thread_session()
            self.logger.debug("Starting compilation of token %d", token.id)

            # Copy token to this session
            self._copy_token_to_session(token, session)
            self.logger.debug("Token %d copied to thread-local session", token.id)

            # Set thread-local session in services
            setattr(self.compilation_service, "session", session)
            setattr(self.validation_service, "session", session)

            # Initial compilation
            self.logger.info("Compiling token %d (%s)", token.id, token.token_type)
            artifact = getattr(self.compilation_service, "compile_token")(
                token.id, llm_client
            )
            if not artifact:
                self.logger.error("Failed to compile token %d", token.id)
                return

            # Validate if requested
            if revalidate:
                self.logger.debug("Validating artifact %d", artifact.id)
                validation_result = self.validation_service.validate_artifact(
                    artifact.id
                )
                if not validation_result.success:
                    error_messages = "; ".join(
                        error.message for error in validation_result.errors
                    )
                    self.logger.warning(
                        "Artifact %d validation failed: %s", artifact.id, error_messages
                    )
                    artifact.valid = False
                    getattr(self.compilation_service, "update_artifact")(artifact)

            # Evaluate all artifacts, regardless of validation status
            self.logger.debug("Evaluating artifact %d", artifact.id)
            evaluation_result = self.evaluation_service.evaluate_code(
                artifact.code,
                {"token_id": token.id, "artifact_id": artifact.id},
            )
            artifact.score = evaluation_result.get("score", 0)
            artifact.feedback = evaluation_result.get(
                "feedback", "No feedback provided"
            )
            getattr(self.compilation_service, "update_artifact")(artifact)
            self.logger.info(
                "Token %d compilation complete: score=%.2f",
                token.id,
                artifact.score,
            )

        except Exception as e:
            self.logger.error(
                "Failed to compile token %s: %s",
                token.token_uuid,
                str(e),
                exc_info=True,
            )
            raise
        finally:
            if session:
                # Remove the session from the registry and close it
                if not isinstance(self.Session, type(lambda: None)):  # Not a lambda
                    self.Session.remove()
                self.logger.debug("Cleaned up session for token %d", token.id)

    def compile_and_validate_parallel(
        self,
        tokens: List[DomainToken],
        llm_client: BaseLLMClient,
        revalidate: bool,
        max_workers: int = 4,
    ) -> None:
        """Compile tokens in parallel when possible.

        Tokens are grouped into levels based on their dependencies, and tokens
        within each level are compiled in parallel.

        Args:
            tokens: List of tokens to compile
            llm_client: LLM client to use for compilation
            revalidate: Whether to validate compiled artifacts
            max_workers: Maximum number of parallel workers
        """
        self.logger.info(
            "Starting parallel compilation of %d tokens with %d workers",
            len(tokens),
            max_workers,
        )

        # Group tokens by their dependency level
        token_levels = self._group_tokens_by_level(tokens)
        self.logger.debug("Grouped tokens into %d dependency levels", len(token_levels))

        # Process each level in sequence, but tokens within a level in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for level_num, level in enumerate(token_levels, 1):
                self.logger.info(
                    "Processing level %d/%d with %d tokens",
                    level_num,
                    len(token_levels),
                    len(level),
                )

                # Create a set to track processed tokens
                processed_tokens = set()
                futures = {}

                # Submit all tokens in this level for parallel processing
                for token in level:
                    if token.id not in processed_tokens:
                        processed_tokens.add(token.id)
                        future = executor.submit(
                            self._compile_token_wrapper, token, llm_client, revalidate
                        )
                        futures[future] = token.id

                # Wait for all tokens in this level to complete
                for future in concurrent.futures.as_completed(futures.keys()):
                    token_id = futures[future]
                    try:
                        future.result()
                        self.logger.debug("Token %d processing complete", token_id)
                    except Exception as e:
                        self.logger.error(
                            "Failed to compile token %d: %s",
                            token_id,
                            str(e),
                            exc_info=True,
                        )
                        raise

                self.logger.info("Completed processing of level %d", level_num)

        self.logger.info("Parallel compilation completed successfully")

    def compile_and_validate(
        self,
        tokens: List[DomainToken],
        llm_client: BaseLLMClient,
        revalidate: bool,
    ) -> None:
        """Compile tokens sequentially.

        Legacy sequential compilation method. Consider using
        compile_and_validate_parallel for better performance when tokens can
        be compiled in parallel.

        Args:
            tokens: List of tokens to compile
            llm_client: LLM client to use for compilation
            revalidate: Whether to validate compiled artifacts
        """
        for tok in tokens:
            self._compile_token_wrapper(tok, llm_client, revalidate)
