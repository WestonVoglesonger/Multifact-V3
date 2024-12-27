from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.domain.models import DomainCompiledMultifact
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact

class ArtifactCacheService:
    """
    A global caching service that maps token hash → compiled artifact code.
    It now operates on domain models instead of raw entities.
    """

    @staticmethod
    def get_artifact_by_hash(token_hash: str, session: Session) -> DomainCompiledMultifact | None:
        """
        Checks if there's a compiled artifact with a token hash equal to `token_hash`.
        Returns a domain model (DomainCompiledMultifact) if found, otherwise None.
        """
        entity_artifact = session.scalars(
            select(CompiledMultifact).where(CompiledMultifact.token_hash == token_hash)
        ).first()

        if entity_artifact is None:
            return None

        return entity_artifact.to_domain_artifact()

    @staticmethod
    def store_artifact(token_hash: str, domain_artifact: DomainCompiledMultifact, session: Session):
        """
        Store an artifact keyed by the token hash, operating in domain models.
        Convert domain_artifact to an entity and then persist it.
        
        If the artifact already exists in the DB (identified by domain_artifact.id),
        you might need to fetch and update it. If it's new (no id), just add it.
        """
        if domain_artifact.id is not None:
            # Existing artifact scenario
            entity_artifact = session.get(CompiledMultifact, domain_artifact.id)
            if not entity_artifact:
                # This would be odd, handle error or log
                pass
            else:
                entity_artifact.code = domain_artifact.code
                entity_artifact.valid = domain_artifact.valid
                entity_artifact.cache_hit = domain_artifact.cache_hit
                entity_artifact.language = domain_artifact.language
                entity_artifact.framework = domain_artifact.framework
                entity_artifact.token_hash = token_hash
        else:
            # New artifact scenario
            entity_artifact = CompiledMultifact(
                ni_token_id=domain_artifact.ni_token_id,
                language=domain_artifact.language,
                framework=domain_artifact.framework,
                code=domain_artifact.code,
                valid=domain_artifact.valid,
                cache_hit=domain_artifact.cache_hit,
                token_hash=token_hash,
                created_at=domain_artifact.created_at
            )
            session.add(entity_artifact)

        session.commit()

        # If needed, update domain_artifact id from DB
        if domain_artifact.id is None:
            # now entity_artifact has an id assigned by DB
            domain_artifact.id = entity_artifact.id

    @staticmethod
    def duplicate_artifact_for_token(token_id: int, source_artifact: DomainCompiledMultifact, session: Session) -> DomainCompiledMultifact:
        """
        Create a new artifact record for a new token_id but with the same code as `source_artifact`.
        Return a new domain artifact after insertion.
        """
        # Convert source domain artifact to entity
        base_entity = CompiledMultifact.to_entity_artifact(source_artifact)
        # Adjust fields as needed for the new artifact
        base_entity.ni_token_id = token_id
        base_entity.cache_hit = True
        # Source artifact token_hash can be reused if domain has it. If not, handle accordingly.
        if source_artifact.id is not None:
            # If it had an id, it might have a token_hash from DB, fetch it if needed
            original_entity = session.get(CompiledMultifact, source_artifact.id)
            if original_entity:
                base_entity.token_hash = original_entity.token_hash

        session.add(base_entity)
        session.commit()
        session.refresh(base_entity)

        # Convert back to domain
        return base_entity.to_domain_artifact()
