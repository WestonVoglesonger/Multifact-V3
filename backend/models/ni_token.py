from pydantic import BaseModel
from typing import Optional

class NITokenRead(BaseModel):
    id: int
    ni_document_id: int
    token_uuid: str
    token_type: Optional[str]
    scene_name: Optional[str]
    component_name: Optional[str]
    order: int
    content: str
    hash: str

    class Config:
        from_attributes = True

class NITokenCreate(BaseModel):
    ni_document_id: int
    token_uuid: str
    token_type: Optional[str]
    scene_name: Optional[str]
    component_name: Optional[str]
    order: int
    content: str
    hash: str