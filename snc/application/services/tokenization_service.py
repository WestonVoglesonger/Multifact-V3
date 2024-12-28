# backend/infrastructure/parsing/tokenization_service.py

import uuid
from typing import List
import hashlib
from snc.domain.models import DomainToken
from snc.infrastructure.parsing.token_tree_builder import TokenTreeBuilder
from snc.infrastructure.parsing.advanced_token import AdvancedToken


class TokenizationService:
    """
    A service that converts raw narrative instruction text into a list of DomainTokens.
    Uses AdvancedToken and TokenTreeBuilder as parsing utilities (infrastructure layer).
    """

    def tokenize_content(self, content: str) -> List[DomainToken]:
        # Build a tree of AdvancedToken objects
        scenes = TokenTreeBuilder.build_tree(content)

        # First pass: convert all tokens and build a name -> token map
        name_to_token = {}  # Maps token names to DomainTokens
        domain_tokens = []

        for scene in scenes:
            scene_tokens = self._convert_advanced_token_to_domain_tokens(scene)
            domain_tokens.extend(scene_tokens)

            # Build the name -> token map
            for token in scene_tokens:
                if token.token_type == "scene":
                    name_to_token[token.scene_name] = token
                elif token.token_type == "component":
                    name_to_token[token.component_name] = token
                elif token.token_type == "function":
                    name_to_token[token.token_name] = token

        # Second pass: resolve dependencies using the name map
        def resolve_dependencies(adv_token: AdvancedToken, domain_token: DomainToken):
            for dep_name in adv_token.dependencies:
                if dep_name in name_to_token:
                    domain_token.add_dependency(name_to_token[dep_name])
            for child in adv_token.children:
                child_domain = next(
                    (
                        t
                        for t in domain_tokens
                        if (
                            (t.token_type == "scene" and t.scene_name == child.name)
                            or (
                                t.token_type == "component"
                                and t.component_name == child.name
                            )
                            or (
                                t.token_type == "function"
                                and t.token_name == child.name
                            )
                        )
                    ),
                    None,
                )
                if child_domain:
                    resolve_dependencies(child, child_domain)

        # Apply dependencies to all top-level scenes
        for scene in scenes:
            scene_domain = next(
                (
                    t
                    for t in domain_tokens
                    if t.token_type == "scene" and t.scene_name == scene.name
                ),
                None,
            )
            if scene_domain:
                resolve_dependencies(scene, scene_domain)

        return domain_tokens

    def _convert_advanced_token_to_domain_tokens(
        self, adv_token: AdvancedToken
    ) -> List[DomainToken]:
        # Recursively convert AdvancedToken and its children
        current_domain_token = self._to_domain_token(adv_token)
        all_tokens = [current_domain_token]

        # Convert children
        for child in adv_token.children:
            child_tokens = self._convert_advanced_token_to_domain_tokens(child)
            all_tokens.extend(child_tokens)

        return all_tokens

    def _to_domain_token(self, adv_token: AdvancedToken) -> DomainToken:
        # Compute hash from adv_token content
        token_hash = adv_token.compute_hash()

        # For domain tokens, we may need a stable UUID. Let's just use a random UUID for now.
        token_uuid = str(uuid.uuid4())

        return DomainToken(
            id=None,
            token_uuid=token_uuid,
            token_name=adv_token.name,
            token_type=adv_token.token_type,
            content=adv_token.get_full_text(),
            hash=token_hash,
            scene_name=adv_token.name if adv_token.token_type == "scene" else None,
            component_name=(
                adv_token.name if adv_token.token_type == "component" else None
            ),
            order=0,  # order can be set later if needed
            dependencies=[],  # dependencies will be resolved in the second pass
        )
