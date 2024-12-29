from typing import List, Tuple
from sqlalchemy.orm import Session
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact


class ArtifactRepository:
    """Repository for managing artifacts."""

    def __init__(self, session: Session):
        """Initialize the repository."""
        self.session = session

    def get_tokens_with_artifacts(
        self, doc_id: int
    ) -> List[Tuple[NIToken, CompiledMultifact]]:
        """Get all tokens with their latest artifacts for a document."""
        # Get all tokens for the document
        tokens = (
            self.session.query(NIToken).filter(NIToken.ni_document_id == doc_id).all()
        )

        # For each token, get its latest artifact
        result = []
        for token in tokens:
            artifact = (
                self.session.query(CompiledMultifact)
                .filter(CompiledMultifact.ni_token_id == token.id)
                .order_by(CompiledMultifact.created_at.desc())
                .first()
            )
            result.append((token, artifact))

        return result
