import re
import hashlib
from typing import List, Optional
from .advanced_token import AdvancedToken


class TokenTreeBuilder:
    """
    Builds a tree of AdvancedToken objects from raw narrative instruction text.
    """

    @classmethod
    def build_tree(cls, content: str) -> List[AdvancedToken]:
        """
        Build a tree of AdvancedToken objects from raw text.
        """
        # Split content into lines and process each line
        lines = content.splitlines()
        current_scene: Optional[AdvancedToken] = None
        current_component: Optional[AdvancedToken] = None
        scenes: List[AdvancedToken] = []
        current_token: Optional[AdvancedToken] = None
        current_lines: List[str] = []

        # Regex patterns for bracket lines
        scene_pattern = re.compile(r"^\s*\[Scene\s*:\s*(.*?)\]\s*$")
        component_pattern = re.compile(r"^\s*\[Component\s*:\s*(.*?)\]\s*$")
        function_pattern = re.compile(r"^\s*\[Function(?:\s*:\s*(.*?))?\]\s*$")
        ref_pattern = re.compile(r"\[REF\s*:\s*(.*?)\]")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            scene_match = scene_pattern.match(line)
            component_match = component_pattern.match(line)
            function_match = function_pattern.match(line)

            # If we hit a new bracket line, process the previous token if any
            if scene_match or component_match or function_match:
                if current_token and current_lines:
                    current_token.lines = current_lines
                    current_token.extract_dependencies()
                    current_lines = []

            if scene_match:
                scene_name = scene_match.group(1)
                current_scene = AdvancedToken("scene", scene_name)
                scenes.append(current_scene)
                current_component = None
                current_token = current_scene
            elif component_match:
                if not current_scene:
                    raise ValueError("Component found outside of scene")
                component_name = component_match.group(1)
                current_component = AdvancedToken("component", component_name)
                current_scene.add_child(current_component)
                current_token = current_component
            elif function_match:
                function_name = function_match.group(1)
                if not function_name:
                    # Generate a hash-based name for unnamed functions
                    function_name = (
                        "func_" + hashlib.sha256(line.encode("utf-8")).hexdigest()[:8]
                    )
                function_token = AdvancedToken("function", function_name)
                if current_component:
                    current_component.add_child(function_token)
                elif current_scene:
                    current_scene.add_child(function_token)
                else:
                    raise ValueError("Function found outside of scene/component")
                current_token = function_token
            else:
                # Regular line - check for [REF:X] references
                refs = ref_pattern.findall(line)
                if refs and current_token:
                    for ref in refs:
                        current_token.dependencies.add(ref.strip())
                current_lines.append(line)

        # Process the last token's lines if any
        if current_token and current_lines:
            current_token.lines = current_lines
            current_token.extract_dependencies()

        # Extract dependencies for all tokens in the tree
        for scene in scenes:
            scene.extract_dependencies()
            for child in scene.children:
                child.extract_dependencies()
                for grandchild in child.children:
                    grandchild.extract_dependencies()

        return scenes
