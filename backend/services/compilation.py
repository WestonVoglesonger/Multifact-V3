from sqlalchemy.orm import Session
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.services.llm_client import LLMClient

class CompilationService:
    @staticmethod
    def compile_token(token_id: int, session: Session) -> CompiledMultifact:
        ni_token = session.query(NIToken).filter(NIToken.id == token_id).first()
        if not ni_token:
            raise ValueError(f"Token with id {token_id} not found")

        existing_artifact = session.query(CompiledMultifact).filter(
            CompiledMultifact.ni_token_id == token_id
        ).first()

        if existing_artifact:
            existing_artifact.cache_hit = True
            session.commit()
            return existing_artifact

        code = LLMClient.generate_code(ni_token.content)

        artifact = CompiledMultifact(
            ni_token_id=token_id,
            language="typescript",
            framework="angular",
            code=code,
            valid=True,
            cache_hit=False
        )
        session.add(artifact)
        session.commit()
        session.refresh(artifact)

        return artifact