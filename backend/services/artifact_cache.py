from sqlalchemy.orm import Session
from backend.entities.compiled_multifact import CompiledMultifact
from sqlalchemy import select

class ArtifactCacheService:
    """
    A global caching service that maps token hash → compiled artifact code.
    This allows reusing artifacts across tokens and documents if the content is identical.
    
    Future improvements:
    - Add a real cache store (like Redis) if needed.
    - Implement LRU or time-based eviction.
    For now, we rely on the DB as a 'cache store'.
    """

    @staticmethod
    def get_artifact_by_hash(token_hash: str, session: Session) -> CompiledMultifact | None:
        """
        Checks if there is a compiled artifact with a token hash equal to `token_hash`.
        If yes, returns it.
        Otherwise, returns None.
        
        Assumes we have modified the CompiledMultifact schema or added a separate table 
        to store hash→artifact code. If we haven't, we must store a hash column in CompiledMultifact or 
        a separate artifact_cache table. For simplicity, let's assume we add a 'hash' column to CompiledMultifact.
        """
        # If we haven't added a hash column yet, let's do so:
        # ALTER TABLE compiled_multifacts ADD COLUMN token_hash TEXT;
        # We'll store the token hash when first creating the artifact.
        return session.scalars(
            select(CompiledMultifact).where(CompiledMultifact.token_hash == token_hash)
        ).first()

    @staticmethod
    def store_artifact(token_hash: str, artifact: CompiledMultifact, session: Session):
        """
        Store an artifact keyed by the token hash. The artifact already in DB.
        Just ensure artifact.token_hash = token_hash and commit.
        """
        artifact.token_hash = token_hash
        session.commit()

    @staticmethod
    def duplicate_artifact_for_token(token_id: int, source_artifact: CompiledMultifact, session: Session) -> CompiledMultifact:
        """
        Create a new artifact record for a new token_id but with the same code as `source_artifact`.
        This is needed if we want each token to have its own artifact record.
        Alternatively, we could reference artifacts from multiple tokens, but let's keep it simple.
        """
        new_art = CompiledMultifact(
            ni_token_id=token_id,
            language=source_artifact.language,
            framework=source_artifact.framework,
            code=source_artifact.code,
            valid=source_artifact.valid,
            cache_hit=True,
            token_hash=source_artifact.token_hash,
        )
        session.add(new_art)
        session.commit()
        session.refresh(new_art)
        return new_art