from sqlalchemy.orm import Session
from typing import List, Tuple
import hashlib

from backend.entities.ni_document import NIDocument
from backend.entities.ni_token import NIToken
from backend.models.ni_document import NIDocumentCreate

class NIService:
    @staticmethod
    def create_ni_document(doc: NIDocumentCreate, session: Session) -> NIDocument:
        ni_doc = NIDocument(content=doc.content, version=doc.version)
        session.add(ni_doc)
        session.commit()
        session.refresh(ni_doc)

        tokens = NIService.tokenize_ni(ni_doc.content)
        for order, (scene_name, token_content) in enumerate(tokens):
            content_hash = NIService.sha256_hash(token_content)
            ni_token = NIToken(
                ni_document_id=ni_doc.id,
                scene_name=scene_name,
                component_name=None,
                order=order,
                content=token_content,
                hash=content_hash
            )
            session.add(ni_token)
        session.commit()
        return ni_doc

    @staticmethod
    def tokenize_ni(content: str) -> List[Tuple[str, str]]:
        lines = content.splitlines()
        scene_tokens = []
        current_scene_name = "DefaultScene"
        current_scene_lines = []

        for line in lines:
            if line.strip().startswith("[Scene:"):
                if current_scene_lines:
                    scene_tokens.append((current_scene_name, "\n".join(current_scene_lines)))
                    current_scene_lines = []
                scene_name = NIService.extract_scene_name(line)
                current_scene_name = scene_name
            else:
                current_scene_lines.append(line)

        if current_scene_lines:
            scene_tokens.append((current_scene_name, "\n".join(current_scene_lines)))

        if not scene_tokens and content.strip():
            scene_tokens.append(("DefaultScene", content.strip()))

        return scene_tokens

    @staticmethod
    def extract_scene_name(line: str) -> str:
        line = line.strip()
        if line.startswith("[Scene:") and line.endswith("]"):
            return line[len("[Scene:"):-1].strip()
        return "UnnamedScene"

    @staticmethod
    def sha256_hash(content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()