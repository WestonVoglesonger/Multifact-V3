"""Service for compiling tokens into code artifacts."""

import logging
import hashlib
import concurrent.futures
from typing import List, Dict, Set, Any, Optional, Callable
from collections import defaultdict
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from concurrent.futures import ThreadPoolExecutor

from snc.domain.models import DomainToken
from snc.application.interfaces.icompilation_service import ICompilationService
from snc.application.interfaces.ivalidation_service import IValidationService
from snc.application.interfaces.icode_evaluation_service import ICodeEvaluationService
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.infrastructure.entities.ni_token import NIToken
from snc.application.interfaces.illm_client import ILLMClient
from snc.database import engine
from snc.application.interfaces.itoken_repository import ITokenRepository


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
        session_factory: Optional[sessionmaker] = None,
        token_repository: Optional[ITokenRepository] = None,
    ):
        """Initialize the token compiler.

        Args:
            compilation_service: Service to use for compilation
            validation_service: Service to use for validation
            session_factory: Optional session factory for parallel compilation
            token_repository: Optional token repository for token management
        """
        self.compilation_service = compilation_service
        self.validation_service = validation_service
        self.session_factory = session_factory
        self.token_repository = token_repository
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
        """Copy a token to a new session.

        Args:
            token: Token to copy
            session: Session to copy to

        Raises:
            ValueError: If token cannot be copied or token_repository is not set
        """
        try:
            if self.token_repository is None:
                raise ValueError("Token repository is required for token copying")

            # Get the document ID for this token
            doc_id = self.token_repository.get_doc_id_for_token_uuid(token.token_uuid)
            if doc_id is None:
                raise ValueError(f"Token {token.token_uuid} not found in database")

            # Create new token in this session
            from snc.infrastructure.entities.ni_token import NIToken

            new_token = NIToken(
                ni_document_id=doc_id,  # Set the document ID
                token_uuid=token.token_uuid,
                token_name=token.token_name,
                token_type=token.token_type,
                scene_name=token.scene_name,
                component_name=token.component_name,
                function_name=token.function_name,
                content=token.content,
                hash=self._generate_hash(token.content),
            )
            session.add(new_token)
            session.flush()  # Ensure ID is generated

        except Exception as e:
            self.logger.error("Failed to copy token %s: %s", token.token_uuid, str(e))
            raise

    def _compile_token_wrapper(
        self,
        token: DomainToken,
        llm_client: ILLMClient,
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
            ValueError: If token ID is None or session is not provided
        """
        if token.id is None:
            self.logger.error("Cannot compile token with None ID")
            raise ValueError("Token ID cannot be None")

        if not session:
            raise ValueError("Session is required for token compilation")

        try:
            self.logger.debug("Starting compilation of token %d", token.id)

            # Copy token to this session
            self._copy_token_to_session(token, session)
            self.logger.debug("Token %d copied to thread-local session", token.id)

            # Set thread-local session in services
            setattr(self.compilation_service, "session", session)
            setattr(self.validation_service, "session", session)

            # Compile the token
            artifact = getattr(self.compilation_service, "compile_token")(token.id, llm_client)
            if not artifact:
                self.logger.error("Failed to compile token %d", token.id)
                raise ValueError(f"Failed to compile token {token.id}")

            # Validate if requested
            if revalidate:
                self.validation_service.validate_artifact(artifact.artifact_id)

        except Exception as e:
            self.logger.error("Failed to compile token %s: %s", token.token_uuid, str(e))
            raise
        finally:
            session.close()

    def compile_and_validate(
        self,
        tokens: List[DomainToken],
        llm_client: ILLMClient,
        revalidate: bool = False,
    ) -> None:
        """Compile and validate a list of tokens.

        Args:
            tokens: List of tokens to compile
            llm_client: LLM client to use for compilation
            revalidate: Whether to revalidate existing artifacts

        Raises:
            ValueError: If session factory is not set for parallel compilation
        """
        if not self.session_factory:
            raise ValueError("Session factory is required for parallel compilation")

        # Create a thread pool for parallel compilation
        with ThreadPoolExecutor() as executor:
            futures = []
            for token in tokens:
                # Create a new session for each token
                session = self.session_factory()
                future = executor.submit(
                    self._compile_token_wrapper,
                    token,
                    llm_client,
                    revalidate,
                    session,
                )
                futures.append(future)

            # Wait for all compilations to complete
            for future in futures:
                future.result()  # This will raise any exceptions that occurred
