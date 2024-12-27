# backend/infrastructure/parsing/tokenization_service.py

import uuid
from typing import List
import hashlib
from backend.domain.models import DomainToken
from backend.infrastructure.parsing.token_tree_builder import TokenTreeBuilder
from backend.infrastructure.parsing.advanced_token import AdvancedToken

class TokenizationService:
    """
    A service that converts raw narrative instruction text into a list of DomainTokens.
    Uses AdvancedToken and TokenTreeBuilder as parsing utilities (infrastructure layer).
    """

    def tokenize_content(self, content: str) -> List[DomainToken]:
        # Build a tree of AdvancedToken objects
        scenes = TokenTreeBuilder.build_tree(content)
        
        # Convert AdvancedTokens (scenes and their children) into DomainTokens
        domain_tokens = []
        for scene in scenes:
            domain_tokens.extend(self._convert_advanced_token_to_domain_tokens(scene))
        return domain_tokens

    def _convert_advanced_token_to_domain_tokens(self, adv_token: AdvancedToken) -> List[DomainToken]:
        # Recursively convert AdvancedToken and its children
        current_domain_token = self._to_domain_token(adv_token)
        all_tokens = [current_domain_token]

        # Convert children
        for child in adv_token.children:
            child_tokens = self._convert_advanced_token_to_domain_tokens(child)
            all_tokens.extend(child_tokens)

            # If needed, link dependencies by name. 
            # For now, we just note that dependencies exist by name in adv_token.dependencies.
            # In a full system, you'd resolve these dependencies after token creation.

        return all_tokens

    def _to_domain_token(self, adv_token: AdvancedToken) -> DomainToken:
        # Compute hash from adv_token content
        token_hash = adv_token.compute_hash()

        # For domain tokens, we may need a stable UUID. Let's just use a random UUID for now.
        token_uuid = str(uuid.uuid4())

        return DomainToken(
            id=None,
            token_uuid=token_uuid,
            token_type=adv_token.token_type,
            content=adv_token.get_full_text(),
            hash=token_hash,
            scene_name=adv_token.name if adv_token.token_type == "scene" else None,
            component_name=adv_token.name if adv_token.token_type == "component" else None,
            order=0,  # order can be set later if needed
            # dependencies can be resolved later by matching names in adv_token.dependencies to domain tokens
        )
