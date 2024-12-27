# File: backend/application/services/document_updater.py

from typing import List
from backend.domain.models import DomainToken, TokenDiffResult
from backend.application.interfaces.idocument_repository import IDocumentRepository
from backend.application.interfaces.itoken_repository import ITokenRepository

class DocumentUpdater:
    def __init__(self, doc_repo: IDocumentRepository, token_repo: ITokenRepository):
        self.doc_repo = doc_repo
        self.token_repo = token_repo

    def apply_diff(self, ni_id: int, new_content: str, diff_result: TokenDiffResult) -> List[DomainToken]:
        """
        Overwrites the doc content with `new_content`, removes tokens/artifacts,
        updates changed tokens, and adds new tokens as needed.
        Returns the newly added tokens as domain objects.
        """
        # 1) Overwrite doc content so old lines won't reappear
        self.doc_repo.update_document_content(ni_id, new_content)
        print(f"DEBUG: doc {ni_id} content updated to:\n{new_content}")

        # 2) Remove old tokens/artifacts
        removed_tokens = [rt[0] for rt in diff_result.removed]
        removed_artifacts = [rt[1] for rt in diff_result.removed if rt[1] is not None]

        print(f"DEBUG: removing {len(removed_tokens)} tokens, {len(removed_artifacts)} artifacts")
        self.token_repo.remove_tokens(removed_tokens, removed_artifacts)

        # 3) Update changed tokens
        print(f"DEBUG: updating {len(diff_result.changed)} changed tokens")
        self.token_repo.update_changed_tokens(diff_result.changed)

        # 4) Add newly created tokens
        print(f"DEBUG: adding {len(diff_result.added)} new tokens")
        newly_added_tokens = self.token_repo.add_new_tokens(ni_id, diff_result.added)

        return newly_added_tokens
