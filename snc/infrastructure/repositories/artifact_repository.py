import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from snc.domain.models import DomainToken, DomainCompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.application.interfaces.iartifact_repository import IArtifactRepository


class ArtifactRepository(IArtifactRepository):
    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(__name__)

    def get_tokens_with_artifacts(
        self, doc_id: int
    ) -> List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]:
        """
        Get all tokens for a document, along with their compiled artifacts (if any).
        Returns a list of (DomainToken, DomainCompiledMultifact|None).
        """
        self.logger.debug(f"Getting tokens with artifacts for doc_id={doc_id}")
        tokens = self.get_all_tokens_for_document(doc_id)
        self.logger.debug(f"Found {len(tokens)} tokens in doc {doc_id}")

        result: List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]] = []
        for t in tokens:
            art = (
                self.session.query(CompiledMultifact)
                .filter(CompiledMultifact.ni_token_id == t.id)
                .first()
            )
            self.logger.debug(
                f"Token ID={t.id}, token_uuid={t.token_uuid}, "
                f"artifact_id={art.id if art else None}"
            )
            result.append((t, self._to_domain_artifact(art) if art else None))

        return result

    def add_artifact(
        self, token_id: int, artifact_type: str, content: Dict[str, Any]
    ) -> None:
        """Add a new compiled artifact for a token."""
        self.logger.info(f"Adding artifact for token {token_id}")
        artifact = CompiledMultifact(
            ni_token_id=token_id,
            artifact_type=artifact_type,
            content=content,
        )
        self.session.add(artifact)
        self.session.commit()

    def get_artifact(self, artifact_id: int) -> Optional[DomainCompiledMultifact]:
        """Retrieve a single DomainCompiledMultifact by DB artifact_id."""
        self.logger.debug(f"Getting artifact with id={artifact_id}")
        art = (
            self.session.query(CompiledMultifact)
            .filter(CompiledMultifact.id == artifact_id)
            .first()
        )
        if art:
            self.logger.debug(f"Found artifact {art.id} for token {art.ni_token_id}")
        else:
            self.logger.debug("Artifact not found")
        return self._to_domain_artifact(art) if art else None

    def _to_domain_artifact(
        self, artifact: CompiledMultifact
    ) -> Optional[DomainCompiledMultifact]:
        """Convert a DB artifact to a domain artifact."""
        if not artifact:
            return None
        return DomainCompiledMultifact(
            id=artifact.id,
            ni_token_id=artifact.ni_token_id,
            artifact_type=artifact.artifact_type,
            content=artifact.content,
        )
