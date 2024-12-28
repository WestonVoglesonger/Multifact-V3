"""
Artifact model.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Artifact:
    """Represents a generated code artifact."""

    id: str
    name: str
    type: str
    code: Optional[str] = None
    description: Optional[str] = None
