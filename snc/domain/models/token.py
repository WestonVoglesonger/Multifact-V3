"""
Domain token model.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DomainToken:
    """Represents a token in the narrative."""

    type: str
    name: str
    description: str
    references: List[str]
    code: Optional[str] = None
