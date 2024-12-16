from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from backend.models.ni_token import NITokenRead
from backend.models.compiled_multifact import CompiledMultifactRead

class NIDocumentCreate(BaseModel):
    content: str
    version: Optional[str] = None

class NIDocumentRead(BaseModel):
    id: int
    content: str
    version: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class NIDocumentDetail(BaseModel):
    id: int
    content: str
    version: Optional[str]
    created_at: datetime
    updated_at: datetime
    tokens: List[NITokenRead]
    artifacts: List[CompiledMultifactRead]

    class Config:
        from_attributes = True