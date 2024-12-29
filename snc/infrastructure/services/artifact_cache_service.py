"""Service for caching and retrieving compiled artifacts."""

from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone

from snc.domain.models import DomainCompiledMultifact
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact


class ArtifactCacheService:
    """Global caching service for compiled artifacts.

    Maps token hashes to compiled artifact code, operating on domain models
    instead of raw entities.
    """

    @staticmethod
    def get_artifact_by_hash(
        token_hash: str, session: Session
    ) -> DomainCompiledMultifact | None:
        """Check for a compiled artifact with matching token hash.

        Args:
            token_hash: Hash to look up
            session: Database session

        Returns:
            Domain model if found, None otherwise
        """
        entity_artifact = session.scalars(
            select(CompiledMultifact).where(
                CompiledMultifact.token_hash == token_hash
            )
        ).first()

        if entity_artifact is None:
            return None

        return entity_artifact.to_domain_artifact()

    @staticmethod
    def store_artifact(
        token_hash: str,
        domain_artifact: DomainCompiledMultifact,
        session: Session,
    ) -> None:
        """Store a new artifact in the cache.

        Args:
            token_hash: Hash to store the artifact under
            domain_artifact: Artifact to store
            session: Database session
        """
        entity = CompiledMultifact.from_domain_artifact(domain_artifact)
        entity.token_hash = token_hash
        session.add(entity)
        session.flush()  # Flush to get the ID
        domain_artifact.id = entity.id  # Update domain object with new ID
        session.commit()

    @staticmethod
    def duplicate_artifact_for_token(
        token_id: int,
        source_artifact: DomainCompiledMultifact,
        session: Session,
    ) -> DomainCompiledMultifact:
        """Create a new artifact record for a token.

        Creates a new artifact with the same code as source_artifact but for
        a different token_id.

        Args:
            token_id: ID of token to create artifact for
            source_artifact: Artifact to duplicate code from
            session: Database session

        Returns:
            New domain artifact after insertion
        """
        # Create a new entity with the same code but different token_id
        new_entity = CompiledMultifact(
            ni_token_id=token_id,
            language=source_artifact.language,
            framework=source_artifact.framework,
            code=source_artifact.code,
            valid=source_artifact.valid,
            cache_hit=True,  # This is a cache hit since we're reusing code
            created_at=datetime.now(timezone.utc),
            score=source_artifact.score,
            feedback=source_artifact.feedback,
        )

        # If source artifact has a token_hash, reuse it
        if source_artifact.id is not None:
            original_entity = session.get(
                CompiledMultifact, source_artifact.id
            )
            if original_entity and original_entity.token_hash:
                new_entity.token_hash = original_entity.token_hash

        session.add(new_entity)
        session.commit()
        session.refresh(new_entity)

        # Convert back to domain
        return new_entity.to_domain_artifact()
