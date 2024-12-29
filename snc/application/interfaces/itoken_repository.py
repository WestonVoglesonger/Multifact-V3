"""Interface for token and artifact repository operations."""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from snc.domain.models import DomainToken, DomainCompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken


class ITokenRepository(ABC):
    """Repository interface for tokens and artifacts.

    Defines the contract for how the application can interact with token data.
    The implementation (SQLAlchemy, etc.) will live in the infrastructure
    layer.
    """

    @abstractmethod
    def get_tokens_with_artifacts(
        self, ni_id: int
    ) -> List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]:
        """Get all tokens and their artifacts for a document.

        Args:
            ni_id: ID of the narrative instruction document

        Returns:
            List of (token, artifact) pairs. Artifact may be None.
        """
        pass

    @abstractmethod
    def remove_tokens(
        self,
        tokens: List[DomainToken],
        artifacts: List[DomainCompiledMultifact],
    ) -> None:
        """Remove tokens and their artifacts from persistence.

        Args:
            tokens: List of tokens to remove
            artifacts: List of artifacts to remove
        """
        pass

    @abstractmethod
    def update_changed_tokens(
        self,
        changed_data: List[
            Tuple[DomainToken, Optional[DomainCompiledMultifact], dict]
        ],
    ) -> None:
        """Update existing tokens and their artifacts.

        Args:
            changed_data: List of (old_token, old_artifact, new_token_data)
                        tuples where old_artifact may be None
        """
        pass

    @abstractmethod
    def add_new_tokens(
        self, ni_id: int, token_data_list: List[dict]
    ) -> List[NIToken]:
        """Add new tokens to a document.

        Args:
            ni_id: ID of the narrative instruction document
            token_data_list: List of token data dictionaries

        Returns:
            List of created tokens
        """
        pass

    @abstractmethod
    def get_artifact(
        self, artifact_id: int
    ) -> Optional[DomainCompiledMultifact]:
        """Get a compiled artifact by ID.

        Args:
            artifact_id: ID of the artifact to retrieve

        Returns:
            The artifact if found, None otherwise
        """
        pass

    @abstractmethod
    def get_token_by_id(self, token_id: int) -> Optional[DomainToken]:
        """Get a token by ID.

        Args:
            token_id: ID of the token to retrieve

        Returns:
            The token if found, None otherwise
        """
        pass

    @abstractmethod
    def get_doc_id_for_token_uuid(self, token_uuid: str) -> Optional[int]:
        """Get document ID for a token UUID.

        Args:
            token_uuid: UUID of the token

        Returns:
            Document ID if found, None otherwise
        """
        pass

    @abstractmethod
    def get_all_tokens_for_document(self, doc_id: int) -> List[DomainToken]:
        """Get all tokens for a document.

        Args:
            doc_id: ID of the document

        Returns:
            List of tokens in the document
        """
        pass
