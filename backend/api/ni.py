from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import db_session
from backend.models.ni_document import NIDocumentCreate, NIDocumentRead, NIDocumentDetail
from backend.services.ni import NIService
from backend.services.compilation import CompilationService
from backend.models.ni_token import NITokenCreate, NITokenRead
from backend.entities.ni_token import NIToken
from sqlalchemy import select

api = APIRouter(prefix="/ni")

openapi_tags = {"name" : "NI", "description" : "NI API"}
@api.post("/upload", response_model=NIDocumentRead, tags=["NI"])
def upload_ni_document(doc: NIDocumentCreate, session: Session = Depends(db_session)):
    ni_doc = NIService.create_ni_document(doc, session)
    return ni_doc

@api.get("/list", response_model=List[NIDocumentRead], tags=["NI"])
def list_ni_documents(session: Session = Depends(db_session)):
    docs = NIService.list_documents(session)
    return docs

@api.get("/{ni_id}", response_model=NIDocumentDetail, tags=["NI"])
def get_ni_document_detail(ni_id: int, session: Session = Depends(db_session)):
    try:
        detail = NIService.get_document_detail(ni_id, session)
        return detail
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@api.post("/update", tags=["NI"])
def update_ni_document(payload: dict, session: Session = Depends(db_session)):
    ni_id = payload.get("ni_id")
    content = payload.get("content")
    if ni_id is None or content is None:
        raise HTTPException(status_code=400, detail="ni_id and content are required")

    try:
        NIService.update_document(ni_id, content, session)
        return {"status": "updated and recompiled"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@api.post("/{ni_id}/recompile", tags=["NI"])
def recompile_document(ni_id: int, session: Session = Depends(db_session)):
    doc = session.get(NIDocumentCreate, ni_id)
    if not doc:
        raise HTTPException(status_code=404, detail="NI document not found")

    tokens = session.scalars(select(NIToken).where(NIToken.ni_document_id == ni_id)).all()
    for t in tokens:
        CompilationService.compile_token(t.id, session)

    return {"status": "recompiled"}