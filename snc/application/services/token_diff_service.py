"""Service for comparing and diffing tokens."""

import hashlib
from typing import Tuple, Optional, List

from snc.domain.models import (
    DomainToken,
    DomainCompiledMultifact,
    TokenDiffResult
)
from snc.application.services.exceptions import (
    TokenDiffError,
    TokenNameCollisionError,
)


class TokenDiffService:
    """Service for comparing and diffing tokens."""

    def diff_tokens(
        self,
        old_tokens: List[Tuple[DomainToken, None | DomainCompiledMultifact]],
        new_tokens_data: List[dict],
    ) -> TokenDiffResult:
        """Compare old tokens with newly parsed token data.

        Compares domain tokens to new token data,
        identifying which tokens are removed, changed, or added.
        """
        old_map = {}
        print("DEBUG: ---- diff_tokens START ----")
        for t, art in old_tokens:
            old_k = self._make_key_from_domain_token(t)
            print(
                "DEBUG: old token "
                f"ID={t.id}, type={t.token_type}, "
                f"name={t.scene_name or t.component_name}, "
                f"key={old_k}"
            )
            if old_k in old_map:
                raise TokenDiffError(
                    f"Duplicate old token key detected: {old_k}"
                )
            old_map[old_k] = (t, art)

        new_map = {}
        for tok_data in new_tokens_data:
            new_k = self._make_key_from_new_token(tok_data)
            print(
                "DEBUG: new token "
                f"type={tok_data['type']}, "
                f"scene={tok_data.get('scene_name')}, "
                f"func={tok_data.get('function_name')}, "
                f"key={new_k}"
            )
            if new_k in new_map:
                raise TokenNameCollisionError(
                    f"Duplicate new token key detected: {new_k}"
                )
            new_map[new_k] = tok_data

        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())

        removed_keys = old_keys - new_keys
        added_keys = new_keys - old_keys
        common_keys = old_keys & new_keys

        print(f"DEBUG: removed_keys={removed_keys}")
        print(f"DEBUG: added_keys={added_keys}")
        print(f"DEBUG: common_keys={common_keys}")

        removed = [old_map[k] for k in removed_keys]
        added = [new_map[k] for k in added_keys]

        changed = []
        for k in common_keys:
            old_token, old_artifact = old_map[k]
            new_tok_data = new_map[k]
            new_hash = self._compute_hash(new_tok_data["content"])
            if old_token.hash != new_hash:
                changed.append((old_token, old_artifact, new_tok_data))
                print(
                    "DEBUG: changed token "
                    f"ID={old_token.id}, "
                    f"old_hash={old_token.hash}, "
                    f"new_hash={new_hash}"
                )

        print(
            "DEBUG: final removed count=", len(removed),
            "added count=", len(added),
            "changed count=", len(changed)
        )
        print("DEBUG: ---- diff_tokens END ----")

        return TokenDiffResult(removed=removed, changed=changed, added=added)

    def _make_key_from_domain_token(
        self,
        t: DomainToken
    ) -> Tuple[str, Optional[str]]:
        """Create a key from a domain token.

        Returns a (token_type, name) tuple for change detection.
        """
        if t.token_type == "scene":
            return ("scene", t.scene_name)
        elif t.token_type == "component":
            return ("component", t.component_name)
        elif t.token_type == "function":
            return ("function", t.token_name)
        return (t.token_type, None)

    def _make_key_from_new_token(self, t: dict) -> Tuple[str, Optional[str]]:
        token_type = t["type"]
        if token_type == "scene":
            return ("scene", t["scene_name"])
        elif token_type == "component":
            return ("component", t["component_name"])
        elif token_type == "function":
            return ("function", t["function_name"])
        return (token_type, None)

    def _extract_function_name_from_content(self, content: str) -> str:
        lines = content.split("\n")
        # If the first line looks like "Name: foo", use that; else hash
        if lines and lines[0].startswith("Name: "):
            return lines[0][6:].strip()
        content_bytes = content.encode("utf-8")
        hash_val = hashlib.sha256(content_bytes).hexdigest()[:8]
        return "func_" + hash_val

    def _generate_function_name_from_content(self, content: str) -> str:
        hash_val = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
        return "func_" + hash_val

    @staticmethod
    def _compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
