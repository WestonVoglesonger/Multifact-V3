import uuid
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.entities.ni_document import NIDocument
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.models.ni_document import NIDocumentCreate, NIDocumentDetail
from backend.models.ni_token import NITokenRead
from backend.models.compiled_multifact import CompiledMultifactRead
from backend.services.compilation import CompilationService
from backend.services.tokenization import TokenTreeBuilder
from backend.models.token_types import AdvancedToken

class NIService:
    @staticmethod
    def create_ni_document(doc: NIDocumentCreate, session: Session) -> NIDocument:
        ni_doc = NIDocument(content=doc.content, version=doc.version)
        session.add(ni_doc)
        session.commit()
        session.refresh(ni_doc)

        top_level_tokens = TokenTreeBuilder.build_tree(ni_doc.content)
        final_tokens = NIService.flatten_tokens(top_level_tokens)

        order = 0
        for t in final_tokens:
            content_hash = t.compute_hash()
            token_uuid = str(uuid.uuid4())
            ni_token = NIToken(
                ni_document_id=ni_doc.id,
                token_uuid=token_uuid,
                token_type=t.token_type,
                scene_name=t.name if t.token_type == "scene" else None,
                component_name=t.name if t.token_type == "component" else None,
                order=order,
                content=t.get_full_text(),
                hash=content_hash
            )
            session.add(ni_token)
            session.commit()
            # Don't compile here automatically, let the compile step happen when needed or from UI
            order += 1

        return ni_doc

    @staticmethod
    def flatten_tokens(tokens: List[AdvancedToken]) -> List[AdvancedToken]:
        result = []
        for t in tokens:
            if t.token_type in ["scene", "component"]:
                result.append(t)
            for c in t.children:
                if c.token_type == "component":
                    result.append(c)
                # Add function-level logic if needed
        return result

    @staticmethod
    def get_document_detail(ni_id: int, session: Session) -> NIDocumentDetail:
        doc = session.query(NIDocument).filter(NIDocument.id == ni_id).one_or_none()
        if not doc:
            raise ValueError(f"NI document {ni_id} not found")

        tokens = session.query(NIToken).filter(NIToken.ni_document_id == ni_id).all()
        token_ids = [t.id for t in tokens]
        artifacts = []
        if token_ids:
            artifacts = session.query(CompiledMultifact).filter(CompiledMultifact.ni_token_id.in_(token_ids)).all()

        return NIDocumentDetail(
            id=doc.id,
            content=doc.content,
            version=doc.version,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            tokens=[NITokenRead.model_validate(t) for t in tokens],
            artifacts=[CompiledMultifactRead.model_validate(a) for a in artifacts]
        )

    @staticmethod
    def update_document(ni_id: int, new_content: str, session: Session):
        # This method will still re-tokenize the entire doc and recreate tokens
        # Useful if we want a full re-tokenization approach. For partial updates,
        # we use token-level endpoints.
        doc = session.query(NIDocument).filter(NIDocument.id == ni_id).one_or_none()
        if not doc:
            raise ValueError(f"NI document {ni_id} not found")

        doc.content = new_content
        # Remove old tokens and artifacts
        old_tokens = session.query(NIToken).filter(NIToken.ni_document_id == ni_id).all()
        for ot in old_tokens:
            session.query(CompiledMultifact).filter(CompiledMultifact.ni_token_id == ot.id).delete()
            session.delete(ot)
        session.commit()

        top_level_tokens = TokenTreeBuilder.build_tree(doc.content)
        final_tokens = NIService.flatten_tokens(top_level_tokens)

        order = 0
        for t in final_tokens:
            content_hash = t.compute_hash()
            token_uuid = str(uuid.uuid4())
            ni_token = NIToken(
                ni_document_id=doc.id,
                token_uuid=token_uuid,
                token_type=t.token_type,
                scene_name=t.name if t.token_type == "scene" else None,
                component_name=t.name if t.token_type == "component" else None,
                order=order,
                content=t.get_full_text(),
                hash=content_hash
            )
            session.add(ni_token)
            session.commit()
            # Compile token
            CompilationService.compile_token(ni_token.id, session)
            order += 1

        return doc
    @staticmethod
    def list_documents(session: Session) -> List[NIDocument]:
        return session.query(NIDocument).order_by(NIDocument.id).all()
