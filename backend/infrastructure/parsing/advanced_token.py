# backend/infrastructure/parsing/advanced_token.py

import re
import hashlib
from typing import List

class AdvancedToken:
    """
    A token representing scenes, components, or functions extracted from narrative instructions.
    Holds lines of text and may have children tokens.
    """
    def __init__(self, token_type: str, name: str):
        self.token_type = token_type
        self.name = name
        self.lines = []
        self.children: List['AdvancedToken'] = []
        self.dependencies = set()

    def add_line(self, line: str):
        # Strip both leading/trailing spaces and newlines
        self.lines.append(line.strip())

    def add_child(self, child: 'AdvancedToken'):
        self.children.append(child)

    def get_full_text(self) -> str:
        return "\n".join(self.lines)

    def compute_hash(self) -> str:
        content = self.get_full_text()
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def extract_dependencies(self, pattern: str = r"REF:([A-Za-z0-9_]+)") -> None:
        dependency_regex = re.compile(pattern)
        for line in self.lines:
            matches = dependency_regex.findall(line)
            for m in matches:
                self.dependencies.add(m)
        for child in self.children:
            child.extract_dependencies(pattern)
