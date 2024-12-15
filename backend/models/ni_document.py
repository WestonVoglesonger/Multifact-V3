from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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
        orm_mode = True