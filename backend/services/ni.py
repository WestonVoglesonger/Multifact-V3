import uuid
import hashlib
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.entities.ni_document import NIDocument
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.models.ni_document import NIDocumentCreate, NIDocumentDetail
from backend.models.ni_token import NITokenRead
from backend.models.compiled_multifact import CompiledMultifactRead
from backend.services.compilation import CompilationService
from backend.services.llm.groq_llm_client import GroqLLMClient
from backend.services.llm.base_llm_client import BaseLLMClient

class NIService:
    """
    Service to create, update, and retrieve NI documents and their associated tokens.
    Uses the LLM to parse the NI content into structured data, then stores tokens and handles compilation.
    """

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self._last_llm_client: Optional[BaseLLMClient] = llm_client

    @staticmethod
    def set_last_llm_client(client: BaseLLMClient):
        NIService._last_llm_client = client

    @staticmethod
    def get_last_llm_client() -> Optional[BaseLLMClient]:
        return NIService._last_llm_client

    @staticmethod
    def create_ni_document(
        doc: NIDocumentCreate, 
        session: Session, 
        llm_client: Optional[BaseLLMClient] = None
    ) -> NIDocument:
        """
        Create a new NI document record, parse it via LLM, and store resulting tokens.

        Args:
            doc (NIDocumentCreate): The data needed to create a new NI document.
            session (Session): SQLAlchemy session.
            llm_client (BaseLLMClient, optional): The LLM client to use. Defaults to GroqLLMClient.

        Returns:
            NIDocument: The newly created NI document record.
        """
        ni_doc = NIDocument(content=doc.content, version=doc.version)
        session.add(ni_doc)
        session.commit()
        session.refresh(ni_doc)

        if llm_client is None:
            llm_client = GroqLLMClient()

        # Store this client as the last used one
        NIService.set_last_llm_client(llm_client)

        structured_data = llm_client.parse_document(ni_doc.content)
        final_tokens = NIService.flatten_llm_output(structured_data)

        order = 0
        for t in final_tokens:
            content_hash = NIService.compute_hash(t["content"])
            token_uuid = str(uuid.uuid4())
            ni_token = NIToken(
                ni_document_id=ni_doc.id,
                token_uuid=token_uuid,
                token_type=t["type"],
                scene_name=t["scene_name"],
                component_name=t["component_name"],
                order=order,
                content=t["content"],
                hash=content_hash
            )
            session.add(ni_token)
            session.commit()
            order += 1

        return ni_doc

    @staticmethod
    def flatten_llm_output(data: dict) -> List[dict]:
        """
        Flatten the LLM JSON into a list of tokens.
        If a function has no name, generate one from its content.
        """
        result = []
        for scene in data.get("scenes", []):
            scene_name = scene.get("name", "UnnamedScene")
            scene_narrative = scene.get("narrative", "")
            result.append({
                "type": "scene",
                "scene_name": scene_name,
                "component_name": None,
                "content": scene_narrative
            })

            for comp in scene.get("components", []):
                comp_name = comp.get("name", "UnnamedComponent")
                comp_narrative = comp.get("narrative", "")
                result.append({
                    "type": "component",
                    "scene_name": None,
                    "component_name": comp_name,
                    "content": comp_narrative
                })

                for func in comp.get("functions", []):
                    func_name = func.get("name")
                    func_narrative = func.get("narrative", "")
                    if not func_name or not func_name.strip():
                        # Generate a stable name from content and component name
                        hash_input = f"{comp_name}:{func_narrative}"
                        stable_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:8]
                        func_name = f"func_{stable_hash}"

                    result.append({
                        "type": "function",
                        "scene_name": None,
                        "component_name": None,
                        "function_name": func_name,
                        "content": func_narrative
                    })

        return result

    @staticmethod
    def compute_hash(content: str) -> str:
        """
        Compute a SHA-256 hash of the given content string.

        Args:
            content (str): The content to hash.

        Returns:
            str: Hexadecimal hash string.
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def get_document_detail(ni_id: int, session: Session) -> NIDocumentDetail:
        """
        Retrieve detailed information about an NI document, including tokens and compiled artifacts.

        Args:
            ni_id (int): The NI document ID.
            session (Session): SQLAlchemy session.

        Returns:
            NIDocumentDetail: Detailed NI document record with tokens and artifacts.
        """
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
    def update_document(ni_id: int, new_content: str, session: Session, llm_client: Optional[BaseLLMClient] = None):
        """
        Update the NI document content and recompile all tokens from scratch using the LLM parser.

        Args:
            ni_id (int): The NI document ID to update.
            new_content (str): The new NI content.
            session (Session): SQLAlchemy session.
            llm_client (BaseLLMClient, optional): The LLM client to use. Defaults to GroqLLMClient.

        Returns:
            NIDocument: The updated NI document record.
        """
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

        if llm_client is None:
            llm_client = GroqLLMClient()

        # Store this client as the last used one
        NIService.set_last_llm_client(llm_client)

        structured_data = llm_client.parse_document(doc.content)
        final_tokens = NIService.flatten_llm_output(structured_data)

        order = 0
        for t in final_tokens:
            content_hash = NIService.compute_hash(t["content"])
            token_uuid = str(uuid.uuid4())
            ni_token = NIToken(
                ni_document_id=doc.id,
                token_uuid=token_uuid,
                token_type=t["type"],
                scene_name=t["scene_name"],
                component_name=t["component_name"],
                order=order,
                content=t["content"],
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
        """
        List all NI documents currently stored.

        Args:
            session (Session): SQLAlchemy session.

        Returns:
            List[NIDocument]: A list of NI document records.
        """
        return session.query(NIDocument).order_by(NIDocument.id).all()
