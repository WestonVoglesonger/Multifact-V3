import logging
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
import uuid
import hashlib
from sqlalchemy import select

from snc.domain.models import DomainToken, DomainCompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.application.interfaces.itoken_repository import ITokenRepository


class TokenRepository(ITokenRepository):
    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(__name__)

    def get_tokens_with_artifacts(
        self, doc_id: int
    ) -> List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]:
        """
        Get all tokens for a document, along with their latest artifact (if any).
        Returns a list of (DomainToken, DomainCompiledMultifact|None).
        """
        self.logger.debug(f"Getting all tokens for document {doc_id}")
        tokens = self.get_all_tokens_for_document(doc_id)
        self.logger.debug(f"Found {len(tokens)} tokens for document {doc_id}")

        result: List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]] = []
        for t in tokens:
            # If multiple artifacts exist, we pick the newest by descending ID.
            art = (
                self.session.query(CompiledMultifact)
                .filter(CompiledMultifact.ni_token_id == t.id)
                .order_by(CompiledMultifact.id.desc())
                .first()
            )
            self.logger.debug(
                f"Token ID={t.id}, token_uuid={t.token_uuid}, "
                f"artifact_id={art.id if art else None}"
            )
            domain_token = t  # t is already a DomainToken
            domain_artifact = art.to_domain_artifact() if art else None
            result.append((domain_token, domain_artifact))

        return result

    def remove_tokens(
        self, tokens: List[DomainToken], artifacts: List[DomainCompiledMultifact]
    ) -> None:
        """
        Remove the given tokens and artifacts from the DB.
        Uses token_uuid for matching tokens, and artifact.id for matching artifacts.
        """
        self.logger.debug(
            f"Removing {len(tokens)} tokens and {len(artifacts)} artifacts"
        )

        token_uuids = [t.token_uuid for t in tokens]
        if token_uuids:
            self.logger.debug(f"Removing tokens with uuids={token_uuids}")
        if artifacts:
            art_ids = [a.id for a in artifacts]
            self.logger.debug(f"Removing artifacts with ids={art_ids}")
            if art_ids:
                self.session.query(CompiledMultifact).filter(
                    CompiledMultifact.id.in_(art_ids)
                ).delete(synchronize_session="fetch")

        # Remove the tokens by token_uuid
        if token_uuids:
            self.session.query(NIToken).filter(
                NIToken.token_uuid.in_(token_uuids)
            ).delete(synchronize_session="fetch")

        self.session.commit()

    def update_changed_tokens(
        self,
        changed_data: List[Tuple[DomainToken, Optional[DomainCompiledMultifact], dict]],
    ) -> None:
        """
        For each changed token, update its DB row with new content, type, etc.
        If there's an old artifact, delete it so a new one can be compiled.
        """
        self.logger.debug(f"Updating {len(changed_data)} changed tokens")
        for old_token, old_artifact, new_data in changed_data:
            self.logger.debug(
                f"Updating token_uuid={old_token.token_uuid}, old_artifact_id={old_artifact.id if old_artifact else None}"
            )
            t_ent = (
                self.session.query(NIToken)
                .filter(NIToken.token_uuid == old_token.token_uuid)
                .one()
            )
            t_ent.content = new_data["content"]
            t_ent.hash = hashlib.sha256(new_data["content"].encode("utf-8")).hexdigest()
            t_ent.token_type = new_data["type"]
            t_ent.scene_name = new_data["scene_name"]
            t_ent.component_name = new_data["component_name"]
            self.session.commit()

            if old_artifact:
                self.logger.debug(f"Removing old artifact {old_artifact.id}")
                self.session.query(CompiledMultifact).filter(
                    CompiledMultifact.id == old_artifact.id
                ).delete()
                self.session.commit()

    def add_new_tokens(
        self, doc_id: int, tokens: List[Dict[str, Any]]
    ) -> List[NIToken]:
        """Add multiple new tokens to a document."""
        self.logger.info(f"Adding {len(tokens)} tokens to document {doc_id}")
        created_tokens = []
        for token_data in tokens:
            token_type = token_data["type"]
            token_name = token_data.get("token_name")
            content = token_data["content"]

            if not token_name:
                raise ValueError(
                    f"Could not determine token_name for token of type {token_type}"
                )

            token = NIToken(
                ni_document_id=doc_id,
                token_uuid=str(uuid.uuid4()),
                token_type=token_type,
                token_name=token_name,
                scene_name=token_name if token_type == "scene" else None,
                component_name=token_name if token_type == "component" else None,
                content=content,
                hash=self._generate_hash(content),
            )
            self.session.add(token)
            created_tokens.append(token)

        self.session.commit()
        return created_tokens

    def get_artifact(self, artifact_id: int) -> Optional[DomainCompiledMultifact]:
        """
        Retrieve a single DomainCompiledMultifact by DB artifact_id.
        """
        self.logger.debug(f"Getting artifact with id={artifact_id}")
        art = (
            self.session.query(CompiledMultifact)
            .filter(CompiledMultifact.id == artifact_id)
            .one_or_none()
        )
        if art:
            self.logger.debug(f"Found artifact {art.id} for token {art.ni_token_id}")
        else:
            self.logger.debug("Artifact not found")
        return self._to_domain_artifact(art) if art else None

    def get_token_by_id(self, token_id: int) -> Optional[DomainToken]:
        """
        Retrieve a domain token by its database ID. Returns None if not found.
        """
        self.logger.debug(f"Getting token with id={token_id}")
        token = self.session.query(NIToken).filter(NIToken.id == token_id).first()
        if not token:
            self.logger.debug("Token not found")
            return None

        return self._to_domain_token(token, cache={})

    def get_doc_id_for_token_uuid(self, token_uuid: str) -> Optional[int]:
        """
        Return the doc_id for which this token_uuid belongs, or None if not found.
        """
        self.logger.debug(f"Getting document ID for token_uuid={token_uuid}")
        t_ent = (
            self.session.query(NIToken)
            .filter(NIToken.token_uuid == token_uuid)
            .one_or_none()
        )
        if t_ent:
            self.logger.debug(
                f"Token {t_ent.id} belongs to document {t_ent.ni_document_id}"
            )
            return t_ent.ni_document_id
        self.logger.debug("Token not found")
        return None

    def get_all_tokens_for_document(self, doc_id: int) -> List[DomainToken]:
        """Return all tokens (as DomainToken) for the given doc."""
        self.logger.debug(f"Getting all tokens for document {doc_id}")
        tokens = (
            self.session.query(NIToken)
            .filter(NIToken.ni_document_id == doc_id)
            .order_by(NIToken.id)
            .all()
        )
        self.logger.debug(f"Found {len(tokens)} tokens for document {doc_id}")

        # Convert to domain tokens
        domain_tokens = []
        for token in tokens:
            self.logger.debug(f"Converting token {token.id}")
            domain_token = DomainToken(
                id=token.id,
                token_uuid=token.token_uuid,
                token_name=token.token_name,
                token_type=token.token_type,
                content=token.content,
                hash=token.hash,
                scene_name=token.scene_name,
                component_name=token.component_name,
                order=token.order,
                dependencies=[],
            )
            domain_tokens.append(domain_token)

        return domain_tokens

    def _to_domain_token(
        self, t: NIToken, cache: Optional[Dict[int, DomainToken]] = None
    ) -> DomainToken:
        """
        Convert an NIToken to a DomainToken. Use a cache dict to avoid infinite recursion
        if the same token or dependency is encountered multiple times.
        """
        if cache is None:
            cache = {}

        if t.id in cache:
            return cache[t.id]

        domain_token = DomainToken(
            id=t.id,
            token_uuid=t.token_uuid,
            token_name=t.token_name,
            token_type=t.token_type,
            content=t.content,
            hash=t.hash,
            scene_name=t.scene_name,
            component_name=t.component_name,
            order=t.order,
            dependencies=[],
        )
        cache[t.id] = domain_token

        # Recursively convert dependencies
        child_tokens = []
        for dep in t.dependencies:
            dep_token = self._to_domain_token(dep, cache)
            child_tokens.append(dep_token)

        domain_token.dependencies = child_tokens
        return domain_token

    def _to_domain_artifact(self, art: CompiledMultifact) -> DomainCompiledMultifact:
        """
        Convert a CompiledMultifact ORM entity into DomainCompiledMultifact.
        """
        return DomainCompiledMultifact(
            artifact_id=art.id,
            ni_token_id=art.ni_token_id,
            language=art.language,
            framework=art.framework,
            code=art.code,
            valid=art.valid,
            cache_hit=art.cache_hit,
            created_at=art.created_at,
            score=art.score,
            feedback=art.feedback,
        )

    def add_new_token(
        self,
        doc_id: int,
        token_type: str,
        token_name: str,
        content: str,
    ) -> NIToken:
        """Add a single new token to the document."""
        token_uuid = str(uuid.uuid4())
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Determine scene_name and component_name based on token type
        scene_name = token_name if token_type == "scene" else None
        component_name = token_name if token_type == "component" else None
        function_name = token_name if token_type == "function" else None

        # Ensure content has the proper format
        if not content.startswith(f"[{token_type.title()}:{token_name}]"):
            content = f"[{token_type.title()}:{token_name}]\n{content}"

        token = NIToken(
            ni_document_id=doc_id,
            token_uuid=token_uuid,
            token_type=token_type,
            token_name=token_name,
            content=content,
            hash=content_hash,
            scene_name=scene_name,
            component_name=component_name,
            function_name=function_name,
        )

        self.logger.debug(f"Creating new token uuid={token_uuid}, type={token_type}")
        self.session.add(token)
        self.session.commit()
        return token

    def _generate_hash(self, content: str) -> str:
        """Generate a hash for the token content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
