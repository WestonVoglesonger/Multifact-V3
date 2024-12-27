import pytest
import hashlib
from backend.infrastructure.parsing.advanced_token import AdvancedToken

def test_advanced_token_init():
    token = AdvancedToken(token_type="scene", name="MainScene")
    assert token.token_type == "scene"
    assert token.name == "MainScene"
    assert token.lines == []
    assert token.children == []
    assert token.dependencies == set()

def test_add_line():
    token = AdvancedToken(token_type="component", name="MyComponent")
    token.add_line("   Some content here   ")
    token.add_line("Another line")
    # Lines are stripped, but kept separate
    assert token.lines == ["Some content here", "Another line"]

def test_add_child():
    parent = AdvancedToken(token_type="scene", name="ParentScene")
    child = AdvancedToken(token_type="component", name="ChildComponent")
    parent.add_child(child)
    assert len(parent.children) == 1
    assert parent.children[0] is child

def test_get_full_text():
    token = AdvancedToken(token_type="function", name="doSomething")
    token.add_line("Line1")
    token.add_line("  Line2 with spaces  ")
    assert token.get_full_text() == "Line1\nLine2 with spaces"

def test_compute_hash():
    token = AdvancedToken(token_type="function", name="testFunc")
    token.add_line("Hello World")
    computed_hash = token.compute_hash()
    
    expected = hashlib.sha256("Hello World".encode("utf-8")).hexdigest()
    assert computed_hash == expected, "compute_hash should match manual SHA-256 of content"

def test_extract_dependencies_no_matches():
    token = AdvancedToken(token_type="scene", name="NoDeps")
    token.add_line("Some text without any refs")
    token.extract_dependencies()
    assert len(token.dependencies) == 0

def test_extract_dependencies_with_matches():
    token = AdvancedToken(token_type="scene", name="Main")
    token.add_line("REF:CompA in this line")
    token.add_line("Also referencing REF:CompB")
    child_token = AdvancedToken(token_type="function", name="doSomething")
    child_token.add_line("Inside function REF:CompC as well")
    token.add_child(child_token)

    token.extract_dependencies()

    # Check top-level dependencies
    assert "CompA" in token.dependencies
    assert "CompB" in token.dependencies
    # Check child's dependencies
    assert "CompC" in child_token.dependencies
