from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from backend.domain.models import DomainToken, DomainCompiledMultifact
from backend.infrastructure.entities.ni_token import NIToken
class ITokenRepository(ABC):
    """
    Defines the contract for how the application can interact with token data.
    The implementation (SQLAlchemy, etc.) will live in the infrastructure layer.
    """

    @abstractmethod
    def get_tokens_with_artifacts(
        self, ni_id: int
    ) -> List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]:
        """
        For a given NI document ID, return a list of (DomainToken, DomainCompiledMultifact?) pairs.
        Each token may or may not have a compiled artifact.
        """
        pass

    @abstractmethod
    def remove_tokens(
        self,
        tokens: List[DomainToken],
        artifacts: List[DomainCompiledMultifact],
    ) -> None:
        """
        Given domain tokens and their artifacts, remove them from persistence.
        """
        pass

    @abstractmethod
    def update_changed_tokens(
        self,
        changed_data: List[Tuple[DomainToken, Optional[DomainCompiledMultifact], dict]],
    ) -> None:
        """
        Update existing tokens (and possibly remove old artifacts) based on new data dict.
        The changed_data tuple typically contains: (old_token, old_artifact, new_token_data).
        """
        pass

    @abstractmethod
    def add_new_tokens(
        self, ni_id: int, token_data_list: List[dict]
    ) -> List[NIToken]:
        """
        Insert newly introduced tokens for a given NI document ID and return domain tokens.
        """
        pass

    @abstractmethod
    def get_artifact(self, artifact_id: int) -> Optional[DomainCompiledMultifact]:
        """
        Retrieve a compiled artifact by its ID.
        Returns None if not found.
        """
        pass

    @abstractmethod
    def get_token_by_id(self, token_id: int) -> Optional[DomainToken]:
        """
        Retrieve a domain token by its database ID. Returns None if not found.
        """
        pass

    @abstractmethod
    def get_doc_id_for_token_uuid(self, token_uuid: str) -> Optional[int]:
        """
        For a given token UUID, retrieve the associated NI document ID (if it exists).
        """
        pass

    @abstractmethod
    def get_all_tokens_for_document(self, doc_id: int) -> List[DomainToken]:
        """
        Retrieve all tokens (as DomainToken) for the given NI document ID.
        """
        pass
