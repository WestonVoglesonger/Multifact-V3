from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.database import db_session
from pydantic import BaseModel
from backend.services.user_intervention import UserInterventionService

api = APIRouter(prefix="/user-intervention")

@api.get("/artifact/{artifact_id}/errors")
def get_artifact_errors(artifact_id: int, session: Session = Depends(db_session)):
    try:
        return UserInterventionService.get_artifact_errors(artifact_id, session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

class NIUpdatePayload(BaseModel):
    ni_id: int
    content: str

@api.post("/ni/update")
def update_ni(payload: NIUpdatePayload, session: Session = Depends(db_session)):
    try:
        UserInterventionService.update_ni_and_recompile(payload.ni_id, payload.content, session)
        return {"status": "updated and recompiled"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))