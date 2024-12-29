# backend/infrastructure/parsing/advanced_token.py

"""Advanced token parsing for narrative instructions."""

import re
import hashlib
from typing import List, Set


class AdvancedToken:
    """Token representing a scene, component, or function.

    Includes support for dependencies and hierarchical relationships between
    tokens in the narrative instruction.
    """

    def __init__(self, token_type: str, name: str):
        """Initialize a new token.

        Args:
            token_type: Type of token (scene, component, function)
            name: Name of the token
        """
        self.token_type = token_type
        self.name = name
        self.lines: List[str] = []
        self.children: List[AdvancedToken] = []
        self.dependencies: Set[str] = set()

    def add_line(self, line: str) -> None:
        """Add a line of content to this token, stripping whitespace.

        Args:
            line: Line of content to add
        """
        self.lines.append(line.strip())

    def add_child(self, child: "AdvancedToken") -> None:
        """Add a child token to this token.

        Args:
            child: Child token to add
        """
        self.children.append(child)

    def get_full_text(self) -> str:
        """Get the full text content of this token.

        Returns:
            Combined text content of all lines
        """
        return "\n".join(self.lines)

    def compute_hash(self) -> str:
        """Compute a hash of the token's content.

        Returns:
            SHA-256 hash of the token's text content
        """
        content = self.get_full_text()
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def extract_dependencies(self) -> None:
        """Extract dependencies from the token's content.

        Dependencies can be marked with [REF:X] or REF:X syntax. Extracts
        dependencies from both the token's content and its children.
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
