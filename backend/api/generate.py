from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import db_session
from backend.models.ni_document import NIDocumentCreate
from backend.services.ni import NIService
from backend.services.compilation import CompilationService
from backend.entities.ni_token import NIToken
from backend.models.compiled_multifact import CompiledMultifactRead

api = APIRouter(prefix="/generate")

class GenerateRequest(BaseModel):
    prompt: str

@api.post("", response_model=CompiledMultifactRead)
def generate_code(req: GenerateRequest, session: Session = Depends(db_session)):
    # 1. Create NI document from the prompt
    doc_data = NIDocumentCreate(content=req.prompt, version="v1")
    ni_doc = NIService.create_ni_document(doc_data, session)

    # 2. Get the first token (assuming there's at least one)
    token = session.query(NIToken).filter(NIToken.ni_document_id == ni_doc.id).first()
    if not token:
        raise HTTPException(status_code=400, detail="No tokens generated from the prompt.")
    
    # 3. Compile the token
    artifact = CompilationService.compile_token(token.id, session)
    return artifact