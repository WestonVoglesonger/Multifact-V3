from typing import Optional
from sqlalchemy.orm import Session
from backend.domain.models import DomainCompiledMultifact
from backend.application.interfaces.iartifact_repository import IArtifactRepository
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact


class ArtifactRepository(IArtifactRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_artifact_by_id(self, artifact_id: int) -> Optional[DomainCompiledMultifact]:
        art = (
            self.session.query(CompiledMultifact)
            .filter(CompiledMultifact.id == artifact_id)
            .one_or_none()
        )
        if art is None:
            return None
        return art.to_domain_artifact()


    def update_artifact_code(
        self, artifact_id: int, new_code: str, valid: bool
    ) -> None:
        art = (
            self.session.query(CompiledMultifact)
            .filter(CompiledMultifact.id == artifact_id)
            .one_or_none()
        )
        if art:
            art.code = new_code
            art.valid = valid
            self.session.commit()
