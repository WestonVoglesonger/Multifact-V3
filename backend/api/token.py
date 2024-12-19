from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.database import db_session
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.services.compilation import CompilationService
from backend.models.ni_token import NITokenRead
from backend.models.compiled_multifact import CompiledMultifactRead
import hashlib

api = APIRouter(prefix="/ni/token")

class TokenUpdateRequest(BaseModel):
    content: str

@api.get("/{token_id}", response_model=NITokenRead, tags=["NI"])
def get_token(token_id: int, session: Session = Depends(db_session)):
    token = session.get(NIToken, token_id)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return token

@api.post("/{token_id}/update", response_model=CompiledMultifactRead, tags=["NI"])
def update_token(token_id: int, req: TokenUpdateRequest, session: Session = Depends(db_session)):
    token = session.get(NIToken, token_id)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    old_hash = token.hash
    new_content = req.content.strip()
    if not new_content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    new_hash = hashlib.sha256(new_content.encode('utf-8')).hexdigest()
    # If hash changed, recompile
    if new_hash != old_hash:
        # Update token content and hash
        token.content = new_content
        token.hash = new_hash
        # Remove old artifact if any
        old_artifact = session.query(CompiledMultifact).filter_by(ni_token_id=token_id).first()
        if old_artifact:
            session.delete(old_artifact)
        session.commit()
        # Compile new artifact
        artifact = CompilationService.compile_token(token_id, session)
        return artifact
    else:
        # Hash unchanged, return existing artifact
        artifact = session.query(CompiledMultifact).filter_by(ni_token_id=token_id).first()
        if not artifact:
            # If no artifact yet, compile now
            artifact = CompilationService.compile_token(token_id, session)
        return artifact