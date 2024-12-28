# tests/services/test_tokenization_service.py

import pytest
from snc.application.services.tokenization_service import TokenizationService
from snc.domain.models import DomainToken
import hashlib
from sqlalchemy.orm import Session


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_tokenization_service_empty_content(db_session: Session):
    """
    Test TokenizationService.tokenize_content with empty content.
    """
    svc = TokenizationService()
    domain_tokens = svc.tokenize_content("")
    assert domain_tokens == [], "Empty content should result in no tokens"


def test_tokenization_service_single_scene(db_session: Session):
    """
    Test TokenizationService.tokenize_content with a single scene.
    """
    svc = TokenizationService()
    content = "[Scene:Intro]\nWelcome to the application."

    domain_tokens = svc.tokenize_content(content)

    assert len(domain_tokens) == 1, "Should tokenize into one scene token."
    token = domain_tokens[0]
    assert token.token_type == "scene"
    assert token.scene_name == "Intro"
    assert token.content == "Welcome to the application."
    assert token.hash == compute_hash("Welcome to the application.")
    assert token.id is None, "DomainToken id should be None before insertion."
    assert token.dependencies == [], "Scene token should have no dependencies."


def test_tokenization_service_with_dependencies(db_session: Session):
    """
    Test TokenizationService.tokenize_content with dependencies (Scene -> Component -> Function).
    """
    svc = TokenizationService()
    content = """
    [Scene:Main]
    Main scene content.
    [Component:Feature]
    Feature component content.
    [Function:doSomething]
    Function doSomething content.
    """.strip()

    domain_tokens = svc.tokenize_content(content)

    assert (
        len(domain_tokens) == 3
    ), "Should tokenize into 3 tokens: scene, component, function."

    # Identify tokens
    scene = next((t for t in domain_tokens if t.token_type == "scene"), None)
    component = next((t for t in domain_tokens if t.token_type == "component"), None)
    function = next((t for t in domain_tokens if t.token_type == "function"), None)

    assert scene, "Scene token should exist."
    assert component, "Component token should exist."
    assert function, "Function token should exist."

    assert scene.scene_name == "Main"
    assert scene.content == "Main scene content."
    assert scene.dependencies == []

    assert component.component_name == "Feature"
    assert component.content == "Feature component content."
    assert component.dependencies == []


def test_tokenization_service_invalid_function_name(db_session: Session):
    """
    Test TokenizationService.tokenize_content when function has no name, expecting a hash-based name.
    """
    svc = TokenizationService()
    content = """
    [Scene:Main]
    Main scene content.
    [Component:Feature]
    Feature component content.
    [Function]
    Function without a name.
    """.strip()

    domain_tokens = svc.tokenize_content(content)

    assert (
        len(domain_tokens) == 3
    ), "Should tokenize into 3 tokens: scene, component, function."

    # Identify the function token
    function = next((t for t in domain_tokens if t.token_type == "function"), None)
    assert function, "Function token should exist."


def test_tokenization_service_multiple_scenes(db_session: Session):
    """
    Test TokenizationService.tokenize_content with multiple scenes and components.
    """
    svc = TokenizationService()
    content = """
    [Scene:Intro]
    Intro scene content.
    [Component:Welcome]
    Welcome component content.
    [Function:displayWelcome]
    Display welcome message.
    
    [Scene:Dashboard]
    Dashboard scene content.
    [Component:Stats]
    Stats component content.
    [Function:fetchStats]
    Fetch statistics data.
    """.strip()

    domain_tokens = svc.tokenize_content(content)

    assert (
        len(domain_tokens) == 6
    ), "Should tokenize into 6 tokens: 2 scenes, 2 components, 2 functions."

    # Check specific tokens
    intro_scene = next((t for t in domain_tokens if t.scene_name == "Intro"), None)
    welcome_comp = next(
        (t for t in domain_tokens if t.component_name == "Welcome"), None
    )

    dashboard_scene = next(
        (t for t in domain_tokens if t.scene_name == "Dashboard"), None
    )
    stats_comp = next((t for t in domain_tokens if t.component_name == "Stats"), None)

    assert intro_scene, "Intro scene should exist."
    assert welcome_comp, "Welcome component should exist."
    assert dashboard_scene, "Dashboard scene should exist."
    assert stats_comp, "Stats component should exist."

    # Verify contents
    assert intro_scene.content == "Intro scene content."
    assert welcome_comp.content == "Welcome component content."
    assert dashboard_scene.content == "Dashboard scene content."
    assert stats_comp.content == "Stats component content."
