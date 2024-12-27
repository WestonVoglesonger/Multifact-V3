from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session
import uuid
import hashlib
from sqlalchemy import select

from backend.domain.models import DomainToken, DomainCompiledMultifact
from backend.infrastructure.entities.ni_token import NIToken
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact
from backend.application.interfaces.itoken_repository import ITokenRepository


class TokenRepository(ITokenRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_tokens_with_artifacts(
        self, doc_id: int
    ) -> List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]:
        """
        Get all tokens for a document, along with their latest artifact (if any).
        Returns a list of (DomainToken, DomainCompiledMultifact|None).
        """
        print(f"DEBUG: get_tokens_with_artifacts for doc_id={doc_id}")
        tokens = self.get_all_tokens_for_document(doc_id)
        print(f"DEBUG: found {len(tokens)} tokens in doc {doc_id}")

        result: List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]] = []
        for t in tokens:
            # If multiple artifacts exist, we pick the newest by descending ID.
            art = (
                self.session.query(CompiledMultifact)
                .filter(CompiledMultifact.ni_token_id == t.id)
                .order_by(CompiledMultifact.id.desc())
                .first()
            )
            print(
                f"DEBUG: token ID={t.id}, token_uuid={t.token_uuid}, artifact_id={art.id if art else None}"
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
        print(
            f"DEBUG: remove_tokens called with {len(tokens)} tokens, {len(artifacts)} artifacts"
        )

        token_uuids = [t.token_uuid for t in tokens]
        if token_uuids:
            print(f"DEBUG: removing tokens with uuids={token_uuids}")
        if artifacts:
            art_ids = [a.id for a in artifacts]
            print(f"DEBUG: removing artifacts with ids={art_ids}")
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
        print(f"DEBUG: update_changed_tokens with {len(changed_data)} items")
        for old_token, old_artifact, new_data in changed_data:
            print(
                f"DEBUG: updating token_uuid={old_token.token_uuid}, old_artifact_id={old_artifact.id if old_artifact else None}"
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
                print(f"DEBUG: removing old artifact {old_artifact.id}")
                self.session.query(CompiledMultifact).filter(
                    CompiledMultifact.id == old_artifact.id
                ).delete()
                self.session.commit()

    def add_new_tokens(
        self, ni_id: int, token_data_list: List[dict]
    ) -> List[NIToken]:
        """
        Insert new tokens for the doc_id. Returns a list of newly created DomainTokens.
        """
        print(f"DEBUG: add_new_tokens: adding {len(token_data_list)} tokens to doc {ni_id}")
        order_count = (
            self.session.query(NIToken).filter(NIToken.ni_document_id == ni_id).count()
        )
        new_ni_tokens: List[NIToken] = []

        for td in token_data_list:
            content_hash = hashlib.sha256(td["content"].encode("utf-8")).hexdigest()
            token_uuid = str(uuid.uuid4())
            print(f"DEBUG: creating new token uuid={token_uuid}, type={td['type']}")

            ni_token = NIToken(
                ni_document_id=ni_id,
                token_uuid=token_uuid,
                token_type=td["type"],
                scene_name=td.get("scene_name"),
                component_name=td.get("component_name"),
                order=order_count,
                content=td["content"],
                hash=content_hash,
            )
            self.session.add(ni_token)
            self.session.commit()

            new_ni_tokens.append(ni_token)
            order_count += 1

        return new_ni_tokens

    def get_artifact(self, artifact_id: int) -> Optional[DomainCompiledMultifact]:
        """
        Retrieve a single DomainCompiledMultifact by DB artifact_id.
        """
        print(f"DEBUG: get_artifact called with artifact_id={artifact_id}")
        art = (
            self.session.query(CompiledMultifact)
            .filter(CompiledMultifact.id == artifact_id)
            .one_or_none()
        )
        if art:
            print(f"DEBUG: found artifact {art.id} for token {art.ni_token_id}")
        else:
            print("DEBUG: artifact not found")
        return self._to_domain_artifact(art) if art else None

    def get_token_by_id(self, token_id: int) -> Optional[DomainToken]:
        """
        Return a DomainToken for the given token_id, or None if not found.
        """
        print(f"DEBUG: get_token_by_id={token_id}")
        t_ent = self.session.query(NIToken).filter(NIToken.id == token_id).one_or_none()
        if not t_ent:
            print("DEBUG: no token found")
            return None
        return self._to_domain_token(t_ent, cache={})

    def get_doc_id_for_token_uuid(self, token_uuid: str) -> Optional[int]:
        """
        Return the doc_id for which this token_uuid belongs, or None if not found.
        """
        print(f"DEBUG: get_doc_id_for_token_uuid={token_uuid}")
        t_ent = (
            self.session.query(NIToken)
            .filter(NIToken.token_uuid == token_uuid)
            .one_or_none()
        )
        if t_ent:
            print(f"DEBUG: token {t_ent.id} belongs to doc {t_ent.ni_document_id}")
            return t_ent.ni_document_id
        print("DEBUG: token not found")
        return None

    def get_all_tokens_for_document(self, doc_id: int) -> List[DomainToken]:
        """
        Return all tokens (as DomainToken) for the given doc.
        """
        print(f"DEBUG: get_all_tokens_for_document doc_id={doc_id}")
        tokens = (
            self.session.query(NIToken)
            .filter(NIToken.ni_document_id == doc_id)
            .all()
        )
        print(f"DEBUG: found {len(tokens)} raw NIToken rows for doc {doc_id}")
        cache: Dict[int, DomainToken] = {}
        domain_tokens = [self._to_domain_token(t, cache) for t in tokens]
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
