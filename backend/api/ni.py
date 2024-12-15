from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import db_session
from backend.models.ni_document import NIDocumentCreate, NIDocumentRead
from backend.services.ni_service import NIService

openapi_tags = {"name" : "NI", "description" : "NI API"}

api = APIRouter(prefix="/ni")

@api.post("/upload", response_model=NIDocumentRead, tags=["NI"])
def upload_ni_document(doc: NIDocumentCreate, session: Session = Depends(db_session)):
    ni_doc = NIService.create_ni_document(doc, session)
    return ni_doc