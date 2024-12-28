"""
Tests for main CLI commands.
"""

import json
from pathlib import Path
from click.testing import CliRunner
from snc.cli.main import cli


def test_version() -> None:
    """Test version command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "SNC version" in result.output


def test_list_tokens() -> None:
    """Test list-tokens command."""
    runner = CliRunner()

    # Test listing all tokens
    result = runner.invoke(cli, ["list-tokens"])
    assert result.exit_code == 0
    assert "Component" in result.output
    assert "Scene" in result.output
    assert "Function" in result.output

    # Test specific token type
    result = runner.invoke(cli, ["list-tokens", "Component"])
    assert result.exit_code == 0
    assert "Component" in result.output
    assert "buttons, forms, layouts" in result.output

    # Test invalid token type
    result = runner.invoke(cli, ["list-tokens", "InvalidType"])
    assert result.exit_code == 0
    assert "Unknown token type" in result.output


def test_analyze(tmp_path: Path) -> None:
    """Test analyze command."""
    runner = CliRunner()

    # Create test narrative file
    narrative = """
    [Component:Button]
    Create a button component.

    [InvalidToken]
    This should cause an error.

    [Component:Form]
    Create a form that [REF:ButtonMissing] uses a non-existent button.
    """

    narrative_file = tmp_path / "test_narrative.txt"
    narrative_file.write_text(narrative)

    # Test analysis
    result = runner.invoke(cli, ["analyze", str(narrative_file)])
    assert result.exit_code == 0
    assert "Found potential issues" in result.output
    assert "Invalid token format" in result.output
    assert "Reference to undefined token" in result.output


def test_dependencies(tmp_path: Path) -> None:
    """Test dependencies command."""
    runner = CliRunner()

    # Create test narrative file
    narrative = """
    [Component:Button]
    Create a button component.

    [Component:Form]
    Create a form that [REF:Button] uses the button.

    [Scene:Dashboard]
    Create a dashboard that [REF:Form] uses the form and [REF:Button] the button.
    """

    narrative_file = tmp_path / "test_deps.txt"
    narrative_file.write_text(narrative)

    # Test text format
    result = runner.invoke(cli, ["dependencies", str(narrative_file)])
    assert result.exit_code == 0
    assert "Button" in result.output
    assert "Form" in result.output
    assert "Dashboard" in result.output

    # Test JSON format
    result = runner.invoke(
        cli, ["dependencies", str(narrative_file), "--format", "json"]
    )
    assert result.exit_code == 0
    deps = json.loads(result.output)
    assert "Dashboard" in deps
    assert "Button" in deps["Form"]
    assert "Form" in deps["Dashboard"]

    # Test DOT format
    result = runner.invoke(
        cli, ["dependencies", str(narrative_file), "--format", "dot"]
    )
    assert result.exit_code == 0
    assert "digraph G {" in result.output
    assert '"Dashboard" -> "Form"' in result.output
    assert '"Form" -> "Button"' in result.output


def test_invalid_file() -> None:
    """Test commands with non-existent file."""
    runner = CliRunner()

    # Test analyze
    result = runner.invoke(cli, ["analyze", "nonexistent.txt"])
    assert result.exit_code == 2
    assert "does not exist" in result.output.lower()

    # Test dependencies
    result = runner.invoke(cli, ["dependencies", "nonexistent.txt"])
    assert result.exit_code == 2
    assert "does not exist" in result.output.lower()
