"""
Domain document model.
"""

from dataclasses import dataclass
from typing import List
from .token import DomainToken


@dataclass
class DomainDocument:
    """Represents a narrative document."""

    tokens: List[DomainToken]
    content: str
