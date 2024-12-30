"""Repository for managing tokens and their compiled artifacts."""

import logging
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
import uuid
import hashlib
from sqlalchemy.sql import text

from snc.domain.models import DomainToken, DomainCompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.application.interfaces.itoken_repository import ITokenRepository


class TokenRepository(ITokenRepository):
    """Repository for managing tokens and their compiled artifacts.

    Provides methods for:
    - Retrieving tokens and artifacts
    - Adding new tokens
    - Updating existing tokens
    - Removing tokens and artifacts
    """

    def __init__(self, session: Session):
        """Initialize the repository.

        Args:
            session: Database session to use
        """
        self.session = session
        self.logger = logging.getLogger(__name__)

    def get_tokens_with_artifacts(
        self, doc_id: int
    ) -> List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]:
        """Get all tokens for a document with their latest artifacts.

        Args:
            doc_id: Document ID to get tokens for

        Returns:
            List of tuples containing (token, artifact) pairs.
            The artifact may be None if not compiled yet.
        """
        self.logger.debug(f"Getting all tokens for document {doc_id}")
        tokens = self.get_all_tokens_for_document(doc_id)
        self.logger.debug(f"Found {len(tokens)} tokens for document {doc_id}")

        result: List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]] = []
        for t in tokens:
            # Get all artifacts for this token
            self.session.expire_all()
            arts = (
                self.session.query(CompiledMultifact)
                .filter(CompiledMultifact.ni_token_id == t.id)
                .order_by(CompiledMultifact.created_at.desc())
                .all()
            )
            self.logger.debug(
                f"Token ID={t.id}, token_uuid={t.token_uuid}, " f"found {len(arts)} artifacts"
            )
            domain_token = t  # t is already a DomainToken
            if arts:
                for art in arts:
                    result.append((domain_token, art.to_domain_artifact()))
            else:
                result.append((domain_token, None))

        return result

    def remove_tokens(
        self,
        tokens: List[DomainToken],
        artifacts: List[DomainCompiledMultifact],
    ) -> None:
        """Remove tokens and artifacts from the database.

        Args:
            tokens: List of tokens to remove
            artifacts: List of artifacts to remove

        Uses token_uuid for matching tokens and artifact.id for artifacts.
        """
        self.logger.debug(f"Removing {len(tokens)} tokens and {len(artifacts)} artifacts")

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
            self.session.query(NIToken).filter(NIToken.token_uuid.in_(token_uuids)).delete(
                synchronize_session="fetch"
            )

        self.session.commit()

    def update_changed_tokens(
        self,
        changed_data: List[Tuple[DomainToken, Optional[DomainCompiledMultifact], dict]],
    ) -> None:
        """Update changed tokens and remove their old artifacts.

        Args:
            changed_data: List of tuples containing:
                - Old token
                - Old artifact (may be None)
                - New token data dictionary
        """
        self.logger.debug(f"Updating {len(changed_data)} changed tokens")
        for old_token, old_artifact, new_data in changed_data:
            self.logger.debug(
                f"Updating token_uuid={old_token.token_uuid}, "
                f"old_artifact_id={old_artifact.id if old_artifact else None}"
            )
            t_ent = (
                self.session.query(NIToken).filter(NIToken.token_uuid == old_token.token_uuid).one()
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

    def add_new_tokens(self, doc_id: int, tokens: List[Dict[str, Any]]) -> List[NIToken]:
        """Add multiple new tokens to a document.

        Args:
            doc_id: Document ID to add tokens to
            tokens: List of token data dictionaries

        Returns:
            List of created NIToken entities

        Raises:
            ValueError: If token_name is missing
        """
        self.logger.info(f"Adding {len(tokens)} tokens to document {doc_id}")
        created_tokens = []
        for token_data in tokens:
            token_type = token_data["type"]
            token_name = token_data.get("token_name")
            content = token_data["content"]

            if not token_name:
                msg = f"Could not determine token_name for token of type " f"{token_type}"
                raise ValueError(msg)

            token = NIToken(
                ni_document_id=doc_id,
                token_uuid=str(uuid.uuid4()),
                token_type=token_type,
                token_name=token_name,
                scene_name=token_name if token_type == "scene" else None,
                component_name=(token_name if token_type == "component" else None),
                function_name=token_data.get(
                    "function_name", token_name if token_type == "function" else None
                ),
                content=content,
                hash=self._generate_hash(content),
            )
            self.session.add(token)
            created_tokens.append(token)

        self.session.commit()
        return created_tokens

    def get_artifact(self, artifact_id: int) -> Optional[DomainCompiledMultifact]:
        """Get a single compiled artifact by ID.

        Args:
            artifact_id: ID of artifact to retrieve

        Returns:
            Domain artifact if found, None otherwise
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
        """Get a single token by ID.

        Args:
            token_id: ID of token to retrieve

        Returns:
            Domain token if found, None otherwise
        """
        self.logger.debug(f"Getting token with id={token_id}")
        token = self.session.query(NIToken).filter(NIToken.id == token_id).first()
        if not token:
            self.logger.debug("Token not found")
            return None

        return self._to_domain_token(token, cache={})

    def get_doc_id_for_token_uuid(self, token_uuid: str) -> Optional[int]:
        """Get document ID for a token UUID.

        Args:
            token_uuid: UUID of token to look up

        Returns:
            Document ID if found, None otherwise
        """
        self.logger.debug(f"Getting document ID for token_uuid={token_uuid}")
        t_ent = self.session.query(NIToken).filter(NIToken.token_uuid == token_uuid).one_or_none()
        if t_ent:
            self.logger.debug(f"Token {t_ent.id} belongs to document {t_ent.ni_document_id}")
            return t_ent.ni_document_id
        self.logger.debug("Token not found")
        return None

    def get_all_tokens_for_document(self, doc_id: int) -> List[DomainToken]:
        """Get all tokens for a document.

        Args:
            doc_id: Document ID to get tokens for

        Returns:
            List of domain tokens with their dependencies
        """
        self.logger.debug(f"Getting all tokens for document {doc_id}")
        tokens = (
            self.session.query(NIToken)
            .filter(NIToken.ni_document_id == doc_id)
            .order_by(NIToken.id)
            .all()
        )
        self.logger.debug(f"Found {len(tokens)} tokens for document {doc_id}")

        # First create all domain tokens
        token_map = {}  # Map of id to domain token
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
            token_map[token.id] = domain_token

        # Then set up dependencies
        for token in tokens:
            domain_token = token_map[token.id]
            for dep in token.dependencies:
                if dep.id in token_map:
                    domain_token.dependencies.append(token_map[dep.id])

        return list(token_map.values())

    def _to_domain_token(
        self, t: NIToken, cache: Optional[Dict[int, DomainToken]] = None
    ) -> DomainToken:
        """Convert an NIToken to a DomainToken.

        Args:
            t: NIToken to convert
            cache: Cache dictionary to avoid infinite recursion

        Returns:
            Converted domain token
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
        """Convert a CompiledMultifact ORM entity into DomainCompiledMultifact.

        Args:
            art: CompiledMultifact entity to convert

        Returns:
            Converted domain artifact
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
            scene_name=scene_name,
            component_name=component_name,
            function_name=function_name,
            content=content,
            hash=content_hash,
        )

        self.logger.debug(f"Creating new token uuid={token_uuid}, type={token_type}")
        self.session.add(token)
        self.session.commit()
        return token

    def _generate_hash(self, content: str) -> str:
        """Generate a hash for the token content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_next_token_id(self) -> Optional[int]:
        """Get the next token ID."""
        try:
            result = self.session.execute(text("SELECT nextval('token_id_seq')"))
            return result.scalar()
        except Exception as e:
            self.logger.error(f"Error getting next token ID: {e}")
            return None

    def create_token(
        self,
        doc_id: int,
        token_type: str,
        token_name: str,
        scene_name: Optional[str],
        component_name: Optional[str],
        function_name: Optional[str],
        content: str,
    ) -> DomainToken:
        """Create a new token.

        Args:
            doc_id: Document ID
            token_type: Token type
            token_name: Token name
            scene_name: Scene name
            component_name: Component name
            function_name: Function name
            content: Token content

        Returns:
            Created domain token
        """
        token = NIToken(
            ni_document_id=doc_id,
            token_uuid=str(uuid.uuid4()),
            token_type=token_type,
            token_name=token_name,
            scene_name=scene_name,
            component_name=component_name,
            function_name=function_name,
            content=content,
            hash=hashlib.sha256(content.encode()).hexdigest(),
        )
        self.session.add(token)
        self.session.flush()  # Get the ID
        return token.to_domain_token()
