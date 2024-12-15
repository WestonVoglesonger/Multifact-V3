from pydantic import BaseModel
from typing import Optional

class NITokenCreate(BaseModel):
    ni_document_id: int
    scene_name: Optional[str]
    component_name: Optional[str]
    order: int
    content: str
    hash: str

class NITokenRead(BaseModel):
    id: int
    ni_document_id: int
    scene_name: Optional[str]
    component_name: Optional[str]
    order: int
    content: str
    hash: str

    class Config:
        orm_mode = True