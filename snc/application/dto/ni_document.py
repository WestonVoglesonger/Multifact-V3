from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from snc.application.dto.ni_token import TokenResponse


class DocumentResponse(BaseModel):
    id: int
    content: str
    version: Optional[str]
    created_at: datetime
    updated_at: datetime
    tokens: List[TokenResponse]
