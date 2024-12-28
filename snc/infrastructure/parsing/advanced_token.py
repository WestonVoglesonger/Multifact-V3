# backend/infrastructure/parsing/advanced_token.py

import re
import hashlib
from typing import List, Set


class AdvancedToken:
    """
    A token that represents a scene, component, or function in the narrative instruction.
    Includes support for dependencies and hierarchical relationships.
    """

    def __init__(self, token_type: str, name: str):
        self.token_type = token_type
        self.name = name
        self.lines: List[str] = []
        self.children: List[AdvancedToken] = []
        self.dependencies: Set[str] = set()

    def add_line(self, line: str) -> None:
        """Add a line of content to this token, stripping whitespace."""
        self.lines.append(line.strip())

    def add_child(self, child: "AdvancedToken") -> None:
        """Add a child token to this token."""
        self.children.append(child)

    def get_full_text(self) -> str:
        """Get the full text content of this token."""
        return "\n".join(self.lines)

    def compute_hash(self) -> str:
        """Compute a hash of the token's content."""
        content = self.get_full_text()
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def extract_dependencies(self) -> None:
        """
        Extract dependencies from the token's content.
        Dependencies can be marked with [REF:X] or REF:X syntax.
        """
        # Check both [REF:X] and REF:X formats
        ref_patterns = [
            re.compile(r"\[REF\s*:\s*(.*?)\]"),  # [REF:X] format
            re.compile(r"REF\s*:\s*(\w+)"),  # REF:X format
        ]

        # Process full text
        content = self.get_full_text()
        for pattern in ref_patterns:
            refs = pattern.findall(content)
            for ref in refs:
                self.dependencies.add(ref.strip())

        # Also check each line individually
        for line in self.lines:
            for pattern in ref_patterns:
                refs = pattern.findall(line)
                for ref in refs:
                    self.dependencies.add(ref.strip())

        # Process children recursively
        for child in self.children:
            child.extract_dependencies()
            # Add child dependencies to parent
            self.dependencies.update(child.dependencies)
