import re
from typing import List, Optional
from backend.infrastructure.parsing.advanced_token import AdvancedToken


class TokenTreeBuilder:
    @staticmethod
    def build_tree(content: str) -> List[AdvancedToken]:
        stripped = content.strip()
        if not stripped:
            return []

        # Regexes that allow possible empty function name
        scene_pattern = re.compile(r"^\[Scene:\s*(.*?)\]$", re.IGNORECASE)
        component_pattern = re.compile(r"^\[Component:\s*(.*?)\]$", re.IGNORECASE)
        # [Function] or [Function: SomeName]
        function_pattern = re.compile(r"^\[Function(?::\s*(.*?))?\]$", re.IGNORECASE)

        lines = content.splitlines()

        scenes: List[AdvancedToken] = []
        current_scene: Optional[AdvancedToken] = None
        current_component: Optional[AdvancedToken] = None
        current_function: Optional[AdvancedToken] = None

        def finalize_function():
            """
            If we have a current function, attach it to current_component if present;
            otherwise attach it to current_scene. Then reset current_function to None.
            """
            nonlocal current_function, current_component, current_scene
            if current_function:
                if current_component:
                    current_component.add_child(current_function)
                else:
                    # If no component, attach to scene directly
                    if not current_scene:
                        current_scene = AdvancedToken("scene", "DefaultScene")
                    current_scene.add_child(current_function)
                current_function = None

        def finalize_component():
            """
            If we have a current component, attach it to the current_scene, then reset.
            """
            nonlocal current_component, current_scene
            if current_component:
                finalize_function()  # make sure to close any open function
                if not current_scene:
                    current_scene = AdvancedToken("scene", "DefaultScene")
                current_scene.add_child(current_component)
                current_component = None

        def finalize_scene():
            """
            If we have a current scene, append it to the scenes list, then reset.
            """
            nonlocal current_scene
            if current_scene:
                finalize_component()  # ensure any open component is closed
                scenes.append(current_scene)
                current_scene = None

        for line in lines:
            raw_line = line.rstrip("\n")  # keep the line, but strip trailing newline
            stripped_line = raw_line.strip()

            # Check for scene bracket
            s_match = scene_pattern.match(stripped_line)
            if s_match:
                # We found a new scene bracket => finalize old scene, start a new one
                finalize_scene()
                scene_name = s_match.group(1).strip() or "UnnamedScene"
                current_scene = AdvancedToken(token_type="scene", name=scene_name)
                continue

            # Check for component bracket
            c_match = component_pattern.match(stripped_line)
            if c_match:
                # We found a new component bracket => finalize old component, start a new one
                finalize_component()
                comp_name = c_match.group(1).strip() or "UnnamedComponent"
                current_component = AdvancedToken("component", comp_name)
                continue

            # Check for function bracket (may have empty name)
            f_match = function_pattern.match(stripped_line)
            if f_match:
                # We found a new function => finalize old function, start a new one
                finalize_function()
                func_name = f_match.group(1) or ""  # might be empty
                current_function = AdvancedToken("function", func_name.strip())
                continue

            # If we reach here, it's a *regular line*
            if current_function:
                # Append line to the function
                current_function.add_line(raw_line)
            elif current_component:
                # Append line to the component
                current_component.add_line(raw_line)
            else:
                # Append line to the scene (create a default if needed)
                if not current_scene:
                    current_scene = AdvancedToken("scene", "DefaultScene")
                current_scene.add_line(raw_line)

        # End of loop => finalize any remaining tokens
        finalize_scene()

        # Extract dependencies for each top-level scene
        for scn in scenes:
            scn.extract_dependencies()

        return scenes
