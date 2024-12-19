"""
This module handles user interventions where the user updates the NI content
and triggers recompilation, or checks artifact errors. It compares old and new tokens,
updates only changed tokens, and recompiles them.
"""

from typing import Dict, Tuple, Optional, Any
from sqlalchemy.orm import Session
from backend.entities.ni_document import NIDocument
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.services.compilation import CompilationService
from backend.services.ni import NIService
from backend.models.ni_token import NITokenRead
from backend.services.validation.validation_service import ValidationService
from backend.services.llm.groq_llm_client import GroqLLMClient
import uuid
from sqlalchemy import select
import hashlib


class UserInterventionService:
    """
    A service that supports manual user interventions, such as updating NI documents,
    re-tokenizing them, and recompiling changed tokens. Also provides methods to retrieve artifact errors.
    """

    @staticmethod
    def update_ni_and_recompile(ni_id: int, new_content: str, session: Session) -> None:
        """
        Update the NI document's content to `new_content`, re-parse it via the Groq LLM, and then recompile 
        only the changed or newly introduced tokens.
        """

        ni_doc = session.query(NIDocument).filter(NIDocument.id == ni_id).first()
        if not ni_doc:
            raise ValueError("NI document not found")

        # Update NI content
        ni_doc.content = new_content
        session.commit()

        # Retrieve old tokens
        old_tokens = session.query(NIToken).filter(NIToken.ni_document_id == ni_id).all()
        old_map = {}
        for t in old_tokens:
            token_key = UserInterventionService.make_key_from_db_token(t)
            artifact = session.query(CompiledMultifact).filter_by(ni_token_id=t.id).first()
            old_map[token_key] = (t, artifact)

        # Use the Groq LLM to parse the updated NI content into structured data
        llm_client = GroqLLMClient()  # Use the Groq-based LLM client
        structured_data = llm_client.parse_document(ni_doc.content)
        new_tokens = NIService.flatten_llm_output(structured_data)

        # Build a new map of tokens
        new_map = {}
        for tok_data in new_tokens:
            key = UserInterventionService.make_key_from_new_token(tok_data)
            new_map[key] = tok_data

        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())

        # Removed tokens
        removed_keys = old_keys - new_keys
        for key in removed_keys:
            old_token, old_artifact = old_map[key]
            if old_artifact:
                session.delete(old_artifact)
            session.delete(old_token)
        session.commit()

        # Determine which tokens need recompilation
        to_recompile = []

        for key in new_keys:
            new_tok = new_map[key]
            new_hash = NIService.compute_hash(new_tok["content"])

            if key in old_map:
                # Existing token
                old_token, old_artifact = old_map[key]
                old_hash = old_token.hash

                if old_hash != new_hash:
                    # Content changed: update the token
                    old_token.content = new_tok["content"]
                    old_token.hash = new_hash
                    old_token.token_type = new_tok["type"]
                    old_token.scene_name = new_tok.get("scene_name")
                    old_token.component_name = new_tok.get("component_name")
                    session.commit()

                    # If there was an old artifact, remove it (it's stale now)
                    if old_artifact:
                        session.delete(old_artifact)
                        session.commit()

                    to_recompile.append(old_token)
                # If unchanged, do nothing
            else:
                # New token scenario
                order = UserInterventionService._next_token_order(ni_id, session)
                token_uuid = str(uuid.uuid4())
                ni_token = NIToken(
                    ni_document_id=ni_doc.id,
                    token_uuid=token_uuid,
                    token_type=new_tok["type"],
                    scene_name=new_tok.get("scene_name"),
                    component_name=new_tok.get("component_name"),
                    order=order,
                    content=new_tok["content"],
                    hash=new_hash
                )
                session.add(ni_token)
                session.commit()

                # New tokens must be compiled initially
                to_recompile.append(ni_token)

        # Recompile changed/new tokens
        for tok in to_recompile:
            artifact = CompilationService.compile_token(tok.id, session)
            # Optionally re-validate here:
            # ValidationService.validate_artifact(artifact.id, session)

    @staticmethod
    def make_key_from_db_token(t: NIToken) -> Tuple[str, Optional[str]]:
        if t.token_type == "scene":
            return ("scene", t.scene_name)
        elif t.token_type == "component":
            return ("component", t.component_name)
        elif t.token_type == "function":
            content = t.content
            if "\n" in content and content.startswith("Name: "):
                func_name = content.split("\n")[0][6:].strip()
            else:
                func_name = (
                    "func_" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
                )
            return ("function", func_name)
        return (t.token_type, None)

    @staticmethod
    def make_key_from_new_token(t: dict) -> Tuple[str, Optional[str]]:
        if t["type"] == "scene":
            return ("scene", t["scene_name"])
        elif t["type"] == "component":
            return ("component", t["component_name"])
        elif t["type"] == "function":
            func_name = t.get("function_name")
            if not func_name:
                func_name = (
                    "func_"
                    + hashlib.sha256(t["content"].encode("utf-8")).hexdigest()[:8]
                )
            return ("function", func_name)
        return (t["type"], None)

    @staticmethod
    def _next_token_order(ni_id: int, session: Session) -> int:
        return session.query(NIToken).filter_by(ni_document_id=ni_id).count()

    @staticmethod
    def get_artifact_errors(artifact_id: int, session: Session) -> Dict[str, Any]:
        artifact = (
            session.query(CompiledMultifact)
            .filter(CompiledMultifact.id == artifact_id)
            .first()
        )
        if not artifact:
            raise ValueError("Artifact not found")

        result = ValidationService.validate_artifact(artifact_id, session)
        token = (
            session.query(NIToken).filter(NIToken.id == artifact.ni_token_id).first()
        )
        if not token:
            raise ValueError("Token not found")

        ni_doc = (
            session.query(NIDocument)
            .filter(NIDocument.id == token.ni_document_id)
            .first()
        )
        if not ni_doc:
            raise ValueError("NI document not found")

        return {
            "artifact_id": artifact_id,
            "valid": artifact.valid,
            "errors": [e.__dict__ for e in result.errors],
            "ni_content": ni_doc.content,
            "token_content": token.content,
            "ni_id": ni_doc.id,
        }
