"""Token compilation service for converting narrative tokens into artifacts."""

import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine

from snc.domain.models import DomainToken, DomainCompiledMultifact
from snc.infrastructure.repositories.artifact_repository import (
    ArtifactRepository
)


class TokenCompiler:
    """Service for compiling narrative tokens into their artifact forms.

    This service handles the compilation of individual tokens and batches of
    tokens, managing database connections and error handling.
    """

    def __init__(self, db_url: str):
        """Initialize the token compiler service.

        Args:
            db_url: Database connection URL
        """
        self.engine = create_engine(db_url)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self.logger = logging.getLogger(__name__)

    def compile_token(
        self, token: DomainToken
    ) -> Optional[DomainCompiledMultifact]:
        """Compile a single token into its artifact form.

        Args:
            token: The token to compile

        Returns:
            The compiled artifact if successful, None if compilation failed
        """
        if token.id is None:
            self.logger.error("Cannot compile token without ID")
            return None

        self.logger.info(
            f"Compiling token {token.id} of type {token.token_type}"
        )

        session = self.Session()
        try:
            artifact_repo = ArtifactRepository(session)

            # Example compilation logic - this should be replaced with actual
            # compilation
            if token.token_type == "scene":
                self.logger.debug(f"Compiling scene token {token.token_name}")
                language = "typescript"
                framework = "react"
                code = f"// Scene: {token.scene_name}\n{token.content}"
            elif token.token_type == "component":
                self.logger.debug(
                    f"Compiling component token {token.token_name}"
                )
                language = "typescript"
                framework = "react"
                code = (
                    f"// Component: {token.component_name}\n{token.content}"
                )
            else:
                self.logger.warning(f"Unknown token type {token.token_type}")
                return None

            # Create and store the artifact
            artifact_repo.add_artifact(
                token.id, language, framework, code
            )

            # Get the created artifact
            artifacts = artifact_repo.get_tokens_with_artifacts(token.id)
            if not artifacts:
                self.logger.error(
                    f"Failed to retrieve created artifact for token {token.id}"
                )
                return None

            return artifacts[0][1]  # Return the artifact part of the tuple

        except Exception as e:
            self.logger.error(f"Error compiling token {token.id}: {str(e)}")
            return None
        finally:
            session.close()

    def compile_tokens(
        self, tokens: List[DomainToken]
    ) -> List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]:
        """Compile multiple tokens in parallel.

        Args:
            tokens: List of tokens to compile

        Returns:
            List of (token, artifact) pairs
        """
        self.logger.info(f"Compiling {len(tokens)} tokens")
        results = []

        for token in tokens:
            try:
                artifact = self.compile_token(token)
                results.append((token, artifact))
                if artifact:
                    self.logger.debug(
                        f"Successfully compiled token {token.id}"
                    )
                else:
                    self.logger.warning(f"Failed to compile token {token.id}")
            except Exception as e:
                self.logger.error(
                    f"Error processing token {token.id}: {str(e)}"
                )
                results.append((token, None))

        return results
