from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.services.llm.groq_llm_client import GroqLLMClient
from backend.services.artifact_cache import ArtifactCacheService
from backend.services.llm.base_llm_client import BaseLLMClient
class CompilationService:
    @staticmethod
    def compile_token(token_id: int, session: Session, llm_client: BaseLLMClient) -> CompiledMultifact:
        ni_token = session.get(NIToken, token_id)
        if not ni_token:
            raise ValueError(f"Token with id {token_id} not found")

        # Check if an artifact already exists for this token (unlikely if we just created the token)
        existing_artifact = session.scalars(
            select(CompiledMultifact).where(CompiledMultifact.ni_token_id == token_id)
        ).first()
        if existing_artifact:
            # Artifact already exists, just return it.
            existing_artifact.cache_hit = True
            session.commit()
            return existing_artifact

        # Check cache by hash
        cached_artifact = ArtifactCacheService.get_artifact_by_hash(ni_token.hash, session)
        if cached_artifact:
            # Duplicate artifact for this new token, mark cache hit
            new_artifact = ArtifactCacheService.duplicate_artifact_for_token(token_id, cached_artifact, session)
            return new_artifact

        if llm_client is None:
            llm_client = OpenAILLMClient()
        # If we reach here, no cached artifact found, generate fresh code
        code = llm_client.generate_code(ni_token.content)
        artifact = CompiledMultifact(
            ni_token_id=token_id,
            language="typescript",
            framework="angular",
            code=code,
            valid=True,
            cache_hit=False,
            token_hash=ni_token.hash
        )
        session.add(artifact)
        session.commit()
        session.refresh(artifact)

        # Store artifact in cache keyed by hash
        ArtifactCacheService.store_artifact(ni_token.hash, artifact, session)

        return artifact