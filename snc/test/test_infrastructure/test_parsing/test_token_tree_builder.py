import pytest
from snc.infrastructure.parsing.token_tree_builder import TokenTreeBuilder
from snc.infrastructure.parsing.advanced_token import AdvancedToken


def test_build_tree_empty():
    result = TokenTreeBuilder.build_tree("")
    assert result == [], "Empty content should yield an empty list."


def test_build_tree_single_scene():
    content = "[Scene:Intro]\nIntro line1\nIntro line2"
    result = TokenTreeBuilder.build_tree(content)
    assert len(result) == 1, "Should have exactly one scene token."
    scene = result[0]
    assert scene.token_type == "scene"
    assert scene.name == "Intro"
    assert scene.get_full_text() == "Intro line1\nIntro line2"
    assert scene.children == []


def test_build_tree_scene_component():
    content = """[Scene:Main]
Scene line
[Component:Feature]
Component line here
"""
    result = TokenTreeBuilder.build_tree(content)
    assert len(result) == 1, "Expect one top-level scene."
    scene = result[0]
    assert scene.name == "Main"
    assert scene.get_full_text() == "Scene line"
    assert len(scene.children) == 1, "Scene should have one child (the component)."

    comp = scene.children[0]
    assert comp.token_type == "component"
    assert comp.name == "Feature"
    assert comp.get_full_text() == "Component line here"
    assert comp.children == []


def test_build_tree_scene_component_function():
    content = """[Scene:Main]
Main scene content
[Component:Feature]
Feature content
[Function:doStuff]
Function line1
Function line2
"""
    scenes = TokenTreeBuilder.build_tree(content)
    assert len(scenes) == 1
    scene = scenes[0]
    assert scene.name == "Main"
    assert scene.get_full_text() == "Main scene content"

    assert len(scene.children) == 1
    comp = scene.children[0]
    assert comp.token_type == "component"
    assert comp.name == "Feature"
    assert comp.get_full_text() == "Feature content"

    assert len(comp.children) == 1
    func = comp.children[0]
    assert func.token_type == "function"
    assert func.name == "doStuff"
    assert func.get_full_text() == "Function line1\nFunction line2"


def test_build_tree_function_no_name():
    content = """[Scene:Main]
Scene line
[Component:Feature]
Feature content
"""
    scenes = TokenTreeBuilder.build_tree(content)
    assert len(scenes) == 1
    scene = scenes[0]
    assert scene.name == "Main"

    assert len(scene.children) == 1
    unnamed_func = scene.children[0]
    assert unnamed_func.token_type == "component"
    assert unnamed_func.get_full_text() == "Feature content"


def test_build_tree_multiple_scenes():
    content = """[Scene:Intro]
Intro line
[Scene:Menu]
Menu line1
Menu line2
"""
    scenes = TokenTreeBuilder.build_tree(content)
    assert len(scenes) == 2

    intro = scenes[0]
    assert intro.name == "Intro"
    assert intro.get_full_text() == "Intro line"
    assert len(intro.children) == 0

    menu = scenes[1]
    assert menu.name == "Menu"
    assert menu.get_full_text() == "Menu line1\nMenu line2"


def test_build_tree_dependencies():
    content = """[Scene:Main]
Has a reference REF:DepOne
[Component:Feature]
REF:DepTwo is here
[Function:doIt]
Function line with REF:DepThree
"""
    scenes = TokenTreeBuilder.build_tree(content)
    assert len(scenes) == 1
    scene = scenes[0]

    # The builder calls `extract_dependencies()` at the end, so it should be done
    assert "DepOne" in scene.dependencies
    feature = scene.children[0]
    assert "DepTwo" in feature.dependencies
    func = feature.children[0]
    assert "DepThree" in func.dependencies
