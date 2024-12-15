# backend/api/compile.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import db_session
from backend.services.compilation import CompilationService
from backend.models.compiled_multifact import CompiledMultifactRead

api = APIRouter(prefix="/compile")

openapi_tags = {"name" : "Compile", "description" : "Compile API"}


@api.post("/token/{token_id}", response_model=CompiledMultifactRead, tags=["Compile"])
def compile_token(token_id: int, session: Session = Depends(db_session)):
    try:
        artifact = CompilationService.compile_token(token_id, session)
        return artifact
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))