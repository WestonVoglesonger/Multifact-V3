import re
import uuid
from typing import List
from backend.models.token_types import AdvancedToken

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