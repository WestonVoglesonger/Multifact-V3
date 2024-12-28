import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine

from snc.domain.models import DomainToken, DomainCompiledMultifact
from snc.application.interfaces.itoken_repository import ITokenRepository
from snc.application.interfaces.iartifact_repository import IArtifactRepository
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository


class TokenCompiler:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self.logger = logging.getLogger(__name__)

    def compile_token(self, token: DomainToken) -> Optional[DomainCompiledMultifact]:
        """
        Compile a single token into its artifact form.
        Returns the compiled artifact if successful, None if compilation failed.
        """
        self.logger.info(f"Compiling token {token.id} of type {token.token_type}")

        session = self.Session()
        try:
            token_repo = TokenRepository(session)
            artifact_repo = ArtifactRepository(session)

            # Example compilation logic - this should be replaced with actual compilation
            if token.token_type == "scene":
                self.logger.debug(f"Compiling scene token {token.token_name}")
                content = {
                    "compiled": True,
                    "original_content": token.content,
                    "scene_name": token.scene_name,
                }
            elif token.token_type == "component":
                self.logger.debug(f"Compiling component token {token.token_name}")
                content = {
                    "compiled": True,
                    "original_content": token.content,
                    "component_name": token.component_name,
                }
            else:
                self.logger.warning(f"Unknown token type {token.token_type}")
                return None

            # Create and store the artifact
            artifact_repo.add_artifact(token.id, token.token_type, content)

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
        """
        Compile multiple tokens in parallel.
        Returns a list of (token, artifact) pairs.
        """
        self.logger.info(f"Compiling {len(tokens)} tokens")
        results = []

        for token in tokens:
            try:
                artifact = self.compile_token(token)
                results.append((token, artifact))
                if artifact:
                    self.logger.debug(f"Successfully compiled token {token.id}")
                else:
                    self.logger.warning(f"Failed to compile token {token.id}")
            except Exception as e:
                self.logger.error(f"Error processing token {token.id}: {str(e)}")
                results.append((token, None))

        return results
