from backend.utils.token_key_util import TokenKeyUtil
from backend.services.compilation import CompilationService
from backend.services.ni import NIService
from backend.entities.ni_document import NIDocument
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from typing import Dict, Tuple, Optional, Any
from sqlalchemy.orm import Session
from backend.services.validation import ValidationService
from backend.services.tokenization import TokenTreeBuilder
from backend.models.token_types import AdvancedToken  # Ensure correct import path

class UserInterventionService:
    @staticmethod
    def update_ni_and_recompile(ni_id: int, new_content: str, session: Session) -> None:
        ni_doc = session.query(NIDocument).filter(NIDocument.id == ni_id).first()
        if not ni_doc:
            raise ValueError("NI document not found")

        # Update NI content
        ni_doc.content = new_content
        session.commit()

        # Fetch old tokens and map them by stable keys
        old_tokens = session.query(NIToken).filter(NIToken.ni_document_id == ni_id).all()
        old_map: Dict[Tuple[str, str], Tuple[NIToken, Optional[CompiledMultifact]]] = {}
        for t in old_tokens:
            token_key = TokenKeyUtil.make_key_from_db_token(t)
            artifact = session.query(CompiledMultifact).filter_by(ni_token_id=t.id).first()
            old_map[token_key] = (t, artifact)

        # Re-tokenize using the new tokenization logic
        top_level_tokens = TokenTreeBuilder.build_tree(ni_doc.content)
        new_tokens = NIService.flatten_tokens(top_level_tokens)

        # Create a new map of tokens keyed by stable keys
        new_map: Dict[Tuple[str, str], AdvancedToken] = {}
        for adv_t in new_tokens:
            token_key = TokenKeyUtil.make_key_from_adv_token(adv_t)
            new_map[token_key] = adv_t

        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())

        # Remove tokens/artifacts no longer present
        removed_keys = old_keys - new_keys
        for key in removed_keys:
            old_token, old_artifact = old_map[key]
            if old_artifact:
                session.delete(old_artifact)
            session.delete(old_token)
        session.commit()

        # Determine which tokens to recompile (changed or new)
        to_recompile = []
        for key in new_keys:
            adv_t = new_map[key]
            new_hash = adv_t.compute_hash()

            if key in old_map:
                # Existing token
                old_token, old_artifact = old_map[key]
                old_hash = old_token.hash
                if old_hash != new_hash:
                    # Changed token: update and recompile
                    old_token.content = adv_t.get_full_text()
                    old_token.hash = new_hash
                    session.commit()

                    if old_artifact:
                        session.delete(old_artifact)
                        session.commit()

                    to_recompile.append(old_token)
                # If unchanged, do nothing
            else:
                # New token
                order = UserInterventionService._next_token_order(ni_id, session)
                new_t = NIToken(
                    ni_document_id=ni_doc.id,
                    scene_name=adv_t.name if adv_t.token_type == "scene" else None,
                    component_name=adv_t.name if adv_t.token_type == "component" else None,
                    order=order,
                    content=adv_t.get_full_text(),
                    hash=new_hash
                )
                session.add(new_t)
                session.commit()
                to_recompile.append(new_t)

        # Recompile only changed/new tokens
        for tok in to_recompile:
            CompilationService.compile_token(tok.id, session)

    @staticmethod
    def _next_token_order(ni_id: int, session: Session) -> int:
        return session.query(NIToken).filter_by(ni_document_id=ni_id).count()

    @staticmethod
    def get_artifact_errors(artifact_id: int, session: Session) -> Dict[str, Any]:
        artifact = session.query(CompiledMultifact).filter(CompiledMultifact.id == artifact_id).first()
        if not artifact:
            raise ValueError("Artifact not found")

        result = ValidationService.validate_artifact(artifact_id, session)
        token = session.query(NIToken).filter(NIToken.id == artifact.ni_token_id).first()
        if not token:
            raise ValueError("Token not found")

        ni_doc = session.query(NIDocument).filter(NIDocument.id == token.ni_document_id).first()
        if not ni_doc:
            raise ValueError("NI document not found")

        return {
            "artifact_id": artifact_id,
            "valid": artifact.valid,
            "errors": [e.__dict__ for e in result.errors],
            "ni_content": ni_doc.content,
            "token_content": token.content,
            "ni_id": ni_doc.id
        }