"""Repository implementation for managing compiled artifacts."""

import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from snc.domain.models import DomainToken, DomainCompiledMultifact
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.application.interfaces.iartifact_repository import IArtifactRepository


class ArtifactRepository(IArtifactRepository):
    """Repository for managing compiled artifacts in the database."""

    def __init__(self, session: Session):
        """Initialize the repository.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.logger = logging.getLogger(__name__)
        self.token_repo = TokenRepository(session)

    def get_artifact_by_id(
        self, artifact_id: int
    ) -> Optional[DomainCompiledMultifact]:
        """Get an artifact by its ID.

        Args:
            artifact_id: ID of the artifact to retrieve

        Returns:
            The artifact if found, None otherwise
        """
        return self.get_artifact(artifact_id)

    def update_artifact_code(
        self, artifact_id: int, new_code: str, valid: bool
    ) -> None:
        """Update the code and validity of an artifact.

        Args:
            artifact_id: ID of the artifact to update
            new_code: New code to set
            valid: Whether the new code is valid
        """
        art = (
            self.session.query(CompiledMultifact)
            .filter(CompiledMultifact.id == artifact_id)
            .first()
        )
        if art:
            art.code = new_code
            art.valid = valid
            self.session.commit()
        else:
            self.logger.warning(f"Artifact {artifact_id} not found for update")

    def get_tokens_with_artifacts(
        self, token_id: int
    ) -> List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]:
        """Get all artifacts for a token.

        Args:
            token_id: ID of the token to get artifacts for

        Returns:
            List of (token, artifact) pairs
        """
        self.logger.debug(f"Getting artifacts for token_id={token_id}")
        art = (
            self.session.query(CompiledMultifact)
            .filter(CompiledMultifact.ni_token_id == token_id)
            .first()
        )

        # For now, we just return a single artifact if found
        if art:
            token = self.token_repo.get_token_by_id(token_id)
            if token:
                return [(token, art.to_domain_artifact())]
        return []

    def add_artifact(
        self, token_id: int, language: str, framework: str, code: str
    ) -> None:
        """Add a new compiled artifact for a token.

        Args:
            token_id: ID of the token this artifact belongs to
            language: Programming language of the code
            framework: Framework used in the code
            code: The actual code content
        """
        self.logger.info(f"Adding artifact for token {token_id}")
        artifact = CompiledMultifact(
            ni_token_id=token_id,
            language=language,
            framework=framework,
            code=code,
            created_at=datetime.now(),
            valid=True,
            cache_hit=False,
            token_hash=None,
            score=None,
            feedback=None,
        )
        self.session.add(artifact)
        self.session.commit()

    def get_artifact(
        self, artifact_id: int
    ) -> Optional[DomainCompiledMultifact]:
        """Retrieve a single DomainCompiledMultifact by DB artifact_id.

        Args:
            artifact_id: ID of the artifact to retrieve

        Returns:
            The artifact if found, None otherwise
        """
        self.logger.debug(f"Getting artifact with id={artifact_id}")
        art = (
            self.session.query(CompiledMultifact)
            .filter(CompiledMultifact.id == artifact_id)
            .first()
        )
        if art:
            self.logger.debug(
                f"Found artifact {art.id} for token {art.ni_token_id}"
            )
            return art.to_domain_artifact()
        self.logger.debug("Artifact not found")
        return None
