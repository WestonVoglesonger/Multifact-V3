# File: snc/application/services/document_updater.py

"""Service for applying document updates and managing token changes."""

import logging
from typing import List

from snc.domain.models import DomainToken, TokenDiffResult
from snc.application.interfaces.idocument_repository import IDocumentRepository
from snc.application.interfaces.itoken_repository import ITokenRepository


class DocumentUpdater:
    """Service for applying document updates and managing token changes."""

    def __init__(self, doc_repo: IDocumentRepository, token_repo: ITokenRepository):
        """Initialize the service.

        Args:
            doc_repo: Repository for document operations
            token_repo: Repository for token operations
        """
        self.doc_repo = doc_repo
        self.token_repo = token_repo
        self.logger = logging.getLogger(__name__)

    def apply_diff(
        self, ni_id: int, new_content: str, diff_result: TokenDiffResult
    ) -> List[DomainToken]:
        """Apply document changes and manage affected tokens.

        Overwrites the document content with new_content, removes old tokens
        and artifacts, updates changed tokens, and adds new tokens as needed.

        Args:
            ni_id: Document ID to update
            new_content: New document content
            diff_result: Result of diffing old and new content

        Returns:
            List of newly added domain tokens
        """
        # 1) Overwrite doc content so old lines won't reappear
        self.doc_repo.update_document_content(ni_id, new_content)
        self.logger.debug("Document %d content updated to:\n%s", ni_id, new_content)

        # 2) Remove old tokens/artifacts
        removed_tokens = [rt[0] for rt in diff_result.removed]
        removed_artifacts = [rt[1] for rt in diff_result.removed if rt[1] is not None]

        self.logger.debug(
            "Removing %d tokens, %d artifacts",
            len(removed_tokens),
            len(removed_artifacts),
        )
        self.token_repo.remove_tokens(removed_tokens, removed_artifacts)

        # 3) Update changed tokens
        self.logger.debug("Updating %d changed tokens", len(diff_result.changed))
        self.token_repo.update_changed_tokens(diff_result.changed)

        # 4) Add newly created tokens
        self.logger.debug("Adding %d new tokens", len(diff_result.added))
        new_entity_tokens = self.token_repo.add_new_tokens(ni_id, diff_result.added)

        # Commit all changes to ensure tokens are persisted
        self.commit_changes()

        newly_added_tokens = [token.to_domain_token() for token in new_entity_tokens]

        return newly_added_tokens

    def commit_changes(self) -> None:
        """Commit any pending changes to the database."""
        # Cast to concrete repository types that have session attribute
        from snc.infrastructure.repositories.document_repository import (
            DocumentRepository,
        )
        from snc.infrastructure.repositories.token_repository import TokenRepository

        if isinstance(self.doc_repo, DocumentRepository):
            self.doc_repo.session.commit()
        if isinstance(self.token_repo, TokenRepository):
            self.token_repo.session.commit()
