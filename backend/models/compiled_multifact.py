from pydantic import BaseModel
from datetime import datetime

class CompiledMultifactCreate(BaseModel):
    ni_token_id: int
    language: str
    framework: str
    code: str
    valid: bool = True
    cache_hit: bool = False

class CompiledMultifactRead(BaseModel):
    id: int
    ni_token_id: int
    language: str
    framework: str
    code: str
    created_at: datetime
    valid: bool
    cache_hit: bool

    class Config:
        from_attributes = True