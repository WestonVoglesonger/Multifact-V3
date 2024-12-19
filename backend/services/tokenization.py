"""
Represents a token parsed from narrative instructions when using a traditional parser.
If using LLM-based parsing, this may no longer be needed.
"""

import re
import uuid
from typing import List
import hashlib

# AdvancedToken class
class AdvancedToken:
    """
    A token representing scenes, components, or functions extracted from narrative instructions.
    Holds lines of text and may have children tokens (e.g. functions in a component).
    """
    def __init__(self, token_type: str, name: str):
        """
        Initialize a new AdvancedToken.

        Args:
            token_type (str): The type of the token, e.g. "scene", "component", "function".
            name (str): The name of this token (e.g. scene name, component name).
        """
        self.token_type = token_type  # "scene", "component", "function"
        self.name = name
        self.lines = []
        self.children: List['AdvancedToken'] = []

    def add_line(self, line: str):
        """
        Add a narrative line to this token.

        Args:
            line (str): The narrative line to add.
        """
        self.lines.append(line.strip('\n'))

    def add_child(self, child: 'AdvancedToken'):
        """
        Add a child token (e.g. function within a component).

        Args:
            child (AdvancedToken): The child token to add.
        """
        self.children.append(child)

    def get_full_text(self) -> str:
        """
        Get the full aggregated text lines of this token.

        Returns:
            str: The concatenated text lines.
        """
        return "\n".join(self.lines)

    def compute_hash(self) -> str:
        """
        Compute a hash of the token's textual content.

        Returns:
            str: The SHA-256 hash of the token content.
        """
        content = self.get_full_text()
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

class TokenTreeBuilder:
    @staticmethod
    def build_tree(content: str) -> List[AdvancedToken]:
        stripped = content.strip()
        if not stripped:
            return []
        lines = content.splitlines()

        scene_pattern = re.compile(r"^\[Scene:\s*(.+?)\]$", re.IGNORECASE)
        component_pattern = re.compile(r"^\[Component:\s*(.+?)\]$", re.IGNORECASE)
        function_pattern = re.compile(r"^\[Function:\s*(.+?)\]$", re.IGNORECASE)

        scenes: List[AdvancedToken] = []
        current_scene = None
        current_component = None

        for line in lines:
            s_match = scene_pattern.match(line.strip())
            if s_match:
                if current_scene:
                    if current_component:
                        current_scene.add_child(current_component)
                        current_component = None
                    scenes.append(current_scene)
                current_scene = AdvancedToken("scene", s_match.group(1))
                continue

            c_match = component_pattern.match(line.strip())
            if c_match:
                if current_component:
                    current_scene.add_child(current_component)
                current_component = AdvancedToken("component", c_match.group(1))
                continue

            f_match = function_pattern.match(line.strip())
            if f_match:
                func_token = AdvancedToken("function", f_match.group(1))
                if current_component:
                    current_component.add_child(func_token)
                elif current_scene:
                    current_scene.add_child(func_token)
                else:
                    if not current_scene:
                        current_scene = AdvancedToken("scene", "DefaultScene")
                    current_scene.add_child(func_token)
                continue

            # Regular line
            if current_component:
                current_component.add_line(line)
            elif current_scene:
                current_scene.add_line(line)
            else:
                if not current_scene:
                    current_scene = AdvancedToken("scene", "DefaultScene")
                current_scene.add_line(line)

        if current_scene:
            if current_component:
                current_scene.add_child(current_component)
            scenes.append(current_scene)

        return scenes