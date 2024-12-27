# File: backend/application/services/token_diff_service.py

import hashlib
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass

from backend.domain.models import DomainToken, DomainCompiledMultifact, TokenDiffResult
from backend.application.services.exceptions import TokenDiffError, TokenNameCollisionError

class TokenDiffService:
    def diff_tokens(
        self,
        old_tokens: List[Tuple[DomainToken, None | DomainCompiledMultifact]],
        new_tokens_data: List[dict]
    ) -> TokenDiffResult:
        """
        Compare old tokens (domain tokens + optional artifacts) to the newly parsed token data,
        returning which are removed, changed, or added.
        """
        old_map = {}
        print("DEBUG: ---- diff_tokens START ----")
        for (t, art) in old_tokens:
            old_k = self._make_key_from_domain_token(t)
            print(f"DEBUG: old token ID={t.id}, type={t.token_type}, name={t.scene_name or t.component_name}, key={old_k}")
            if old_k in old_map:
                raise TokenDiffError(f"Duplicate old token key detected: {old_k}")
            old_map[old_k] = (t, art)

        new_map = {}
        for tok_data in new_tokens_data:
            new_k = self._make_key_from_new_token(tok_data)
            print(f"DEBUG: new token type={tok_data['type']}, scene={tok_data.get('scene_name')}, func={tok_data.get('function_name')}, key={new_k}")
            if new_k in new_map:
                raise TokenNameCollisionError(f"Duplicate new token key detected: {new_k}")
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
                print(f"DEBUG: changed token ID={old_token.id}, old_hash={old_token.hash}, new_hash={new_hash}")

        print(f"DEBUG: final removed count={len(removed)}, added count={len(added)}, changed count={len(changed)}")
        print("DEBUG: ---- diff_tokens END ----")

        return TokenDiffResult(removed=removed, changed=changed, added=added)

    def _make_key_from_domain_token(self, t: DomainToken) -> Tuple[str, Optional[str]]:
        """
        Produce a (token_type, name) key so we can detect changes or removals.
        """
        if t.token_type == "scene":
            return ("scene", t.scene_name)
        elif t.token_type == "component":
            return ("component", t.component_name)
        elif t.token_type == "function":
            func_name = self._extract_function_name_from_content(t.content)
            return ("function", func_name)
        # fallback: just use token_type
        return (t.token_type, None)

    def _make_key_from_new_token(self, t: dict) -> Tuple[str, Optional[str]]:
        token_type = t["type"]
        if token_type == "scene":
            return ("scene", t["scene_name"])
        elif token_type == "component":
            return ("component", t["component_name"])
        elif token_type == "function":
            func_name = t.get("function_name")
            if not func_name:
                func_name = self._generate_function_name_from_content(t["content"])
            return ("function", func_name)
        return (token_type, None)

    def _extract_function_name_from_content(self, content: str) -> str:
        lines = content.split("\n")
        # If the first line looks like "Name: foo", use that; else hash
        if lines and lines[0].startswith("Name: "):
            return lines[0][6:].strip()
        return "func_" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]

    def _generate_function_name_from_content(self, content: str) -> str:
        return "func_" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]

    @staticmethod
    def _compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
