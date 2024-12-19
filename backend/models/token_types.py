import hashlib
from typing import List

class AdvancedToken:
    def __init__(self, token_type: str, name: str):
        self.token_type = token_type  # "scene", "component", "function"
        self.name = name
        self.lines = []
        self.children: List['AdvancedToken'] = []

    def add_line(self, line: str):
        self.lines.append(line)

    def add_child(self, child: 'AdvancedToken'):
        self.children.append(child)

    def get_full_text(self) -> str:
        return "\n".join(self.lines)

    def compute_hash(self) -> str:
        content = self.get_full_text()
        return hashlib.sha256(content.encode('utf-8')).hexdigest()