from pydantic import BaseModel
from typing import Optional, List


class TokenResponse(BaseModel):
    uuid: str
    type: str
    token_name: Optional[str] = None
    scene_name: Optional[str] = None
    component_name: Optional[str] = None
    content: str
    hash: str
    order: int
    dependencies: List[str]
