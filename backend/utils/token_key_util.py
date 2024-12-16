# backend/utils/token_key_util.py
from typing import Tuple
from backend.models.token_types import AdvancedToken
from backend.entities.ni_token import NIToken


class TokenKeyUtil:
    @staticmethod
    def make_key_from_adv_token(token: AdvancedToken) -> Tuple[str, str]:
        return (token.token_type, token.name)

    @staticmethod
    def make_key_from_db_token(token: NIToken) -> Tuple[str, str]:
        if token.scene_name is not None:
            return ("scene", token.scene_name)
        elif token.component_name is not None:
            return ("component", token.component_name)
        else:
            return ("unknown", f"token_{token.id}")
