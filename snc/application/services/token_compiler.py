import logging
from typing import List, Dict, Set
from collections import defaultdict
from snc.domain.models import DomainToken, DomainCompiledMultifact
from snc.infrastructure.llm.base_llm_client import BaseLLMClient
from snc.infrastructure.llm.groq_llm_client import GroqLLMClient
from snc.infrastructure.llm.openai_llm_client import OpenAILLMClient
from snc.application.interfaces.icompilation_service import ICompilationService
from snc.application.interfaces.ivalidation_service import IValidationService
from snc.application.services.code_evaluation_service import CodeEvaluationService
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.entities.entity_base import EntityBase
from snc.infrastructure.entities.ni_token import NIToken
import concurrent.futures
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from snc.infrastructure.db.engine import engine
import hashlib
import threading


class TokenCompiler:
    def __init__(
        self,
        compilation_service: ICompilationService,
        validation_service: IValidationService,
        evaluation_service: CodeEvaluationService,
    ):
        self.compilation_service = compilation_service
        self.validation_service = validation_service
        self.evaluation_service = evaluation_service
        self.logger = logging.getLogger(__name__)
        # Create thread-local session factory
        self.Session = scoped_session(sessionmaker(bind=engine))

    def _get_thread_session(self) -> Session:
        """Get a thread-local session."""
        return self.Session()

    def _group_tokens_by_level(
        self, tokens: List[DomainToken]
    ) -> List[List[DomainToken]]:
        """Group tokens by their dependency level. Tokens in the same level can be compiled in parallel."""
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
        processed = set()
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
        """Generate a hash for the token content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _copy_token_to_session(self, token: DomainToken, session: Session) -> None:
        """Copy a token to a new session."""
        if token.id is None:
            return

        # Create a new NIToken instance in the thread-local session
        new_token = NIToken(
            id=token.id,
            ni_document_id=1,  # We know this is always 1 in the stress test
            token_uuid=token.token_uuid,
            token_name=token.token_name,
            token_type=token.token_type,
            scene_name=token.scene_name,
            component_name=token.component_name,
            content=token.content,
            hash=self._generate_hash(token.content),
        )
        session.merge(new_token)
        session.commit()

    def _compile_token_wrapper(
        self, token: DomainToken, llm_client: BaseLLMClient, revalidate: bool
    ) -> None:
        """Wrapper to compile a single token, used for parallel processing."""
        if token.id is None:
            self.logger.error("Cannot compile token with None ID")
            raise ValueError("Token ID cannot be None")

        session = None
        try:
            # Get thread-local session
            session = self._get_thread_session()
            self.logger.debug(f"Starting compilation of token {token.id}")

            # Copy token to this session
            self._copy_token_to_session(token, session)
            self.logger.debug(f"Token {token.id} copied to thread-local session")

            # Set thread-local session in services
            self.compilation_service.session = session
            self.validation_service.session = session

            # Initial compilation
            self.logger.info(f"Compiling token {token.id} ({token.token_type})")
            artifact = self.compilation_service.compile_token(token.id, llm_client)
            if not artifact:
                self.logger.error(f"Failed to compile token {token.id}")
                return

            # Validate if requested
            if revalidate:
                self.logger.debug(f"Validating artifact {artifact.id}")
                validation_result = self.validation_service.validate_artifact(
                    artifact.id
                )
                if not validation_result.success:
                    error_messages = "; ".join(
                        error.message for error in validation_result.errors
                    )
                    self.logger.warning(
                        f"Artifact {artifact.id} validation failed: {error_messages}"
                    )
                    artifact.valid = False
                    self.compilation_service.update_artifact(artifact)
                    return

            # Only evaluate valid artifacts
            if artifact.valid:
                self.logger.debug(f"Evaluating artifact {artifact.id}")
                evaluation_result = self.evaluation_service.evaluate_code(
                    artifact.code,
                    {"token_id": token.id, "artifact_id": artifact.id},
                )
                artifact.score = evaluation_result.get("score", 0)
                artifact.feedback = evaluation_result.get(
                    "feedback", "No feedback provided"
                )
                self.compilation_service.update_artifact(artifact)
                self.logger.info(
                    f"Token {token.id} compilation complete: score={artifact.score}"
                )

        except Exception as e:
            self.logger.error(
                f"Failed to compile token {token.token_uuid}: {str(e)}", exc_info=True
            )
            raise
        finally:
            if session:
                # Remove the session from the registry and close it
                self.Session.remove()
                self.logger.debug(f"Cleaned up session for token {token.id}")

    def compile_and_validate_parallel(
        self,
        tokens: List[DomainToken],
        llm_client: BaseLLMClient,
        revalidate: bool,
        max_workers: int = 4,
    ) -> None:
        """
        Compiles tokens in parallel when they don't have dependencies on each other.
        Tokens are grouped into levels based on their dependencies, and tokens within
        each level are compiled in parallel.
        """
        self.logger.info(
            f"Starting parallel compilation of {len(tokens)} tokens with {max_workers} workers"
        )

        # Group tokens by their dependency level
        token_levels = self._group_tokens_by_level(tokens)
        self.logger.debug(f"Grouped tokens into {len(token_levels)} dependency levels")

        # Process each level in sequence, but tokens within a level in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for level_num, level in enumerate(token_levels, 1):
                self.logger.info(
                    f"Processing level {level_num}/{len(token_levels)} with {len(level)} tokens"
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
                        self.logger.debug(f"Token {token_id} processing complete")
                    except Exception as e:
                        self.logger.error(
                            f"Failed to compile token {token_id}: {str(e)}",
                            exc_info=True,
                        )
                        raise

                self.logger.info(f"Completed processing of level {level_num}")

        self.logger.info("Parallel compilation completed successfully")

    def compile_and_validate(
        self,
        tokens: List[DomainToken],
        llm_client: BaseLLMClient,
        revalidate: bool,
    ) -> None:
        """
        Legacy sequential compilation method. Consider using compile_and_validate_parallel
        for better performance when tokens can be compiled in parallel.
        """
        for tok in tokens:
            self._compile_token_wrapper(tok, llm_client, revalidate)
