"""
Tests for configuration management commands.
"""

import json
import os
from pathlib import Path
from click.testing import CliRunner
from snc.cli.config_cmd import config


def test_config_set(tmp_path: Path) -> None:
    """Test config set command."""
    runner = CliRunner()
    env_file = tmp_path / ".env"

    # Test setting valid values
    result = runner.invoke(
        config, ["set", "LOG_LEVEL", "DEBUG", "--env-file", str(env_file)]
    )
    assert result.exit_code == 0
    assert "Successfully set LOG_LEVEL" in result.output

    # Test setting invalid key
    result = runner.invoke(
        config, ["set", "INVALID_KEY", "value", "--env-file", str(env_file)]
    )
    assert result.exit_code == 0
    assert "Invalid configuration key" in result.output

    # Test setting invalid value
    result = runner.invoke(
        config, ["set", "LOG_LEVEL", "INVALID", "--env-file", str(env_file)]
    )
    assert result.exit_code == 0
    assert "Invalid value for LOG_LEVEL" in result.output


def test_config_get(tmp_path: Path) -> None:
    """Test config get command."""
    runner = CliRunner()
    env_file = tmp_path / ".env"

    # Set up test environment
    env_content = """
    LOG_LEVEL=DEBUG
    DATABASE_URL=sqlite:///test.db
    OPENAI_API_KEY=sk-1234567890abcdef1234567890abcdef1234567890abcdef1234
    """
    env_file.write_text(env_content.strip())

    # Test getting all values
    result = runner.invoke(config, ["get", "--env-file", str(env_file)])
    assert result.exit_code == 0
    assert "LOG_LEVEL=DEBUG" in result.output
    assert "DATABASE_URL=sqlite:///test.db" in result.output
    assert "sk-12345678...7890" in result.output  # Check masking

    # Test getting specific value
    result = runner.invoke(config, ["get", "LOG_LEVEL", "--env-file", str(env_file)])
    assert result.exit_code == 0
    assert "LOG_LEVEL=DEBUG" in result.output

    # Test getting non-existent value
    result = runner.invoke(config, ["get", "NONEXISTENT", "--env-file", str(env_file)])
    assert result.exit_code == 0
    assert "Key not found" in result.output


def test_config_backup_restore(tmp_path: Path) -> None:
    """Test config backup and restore commands."""
    runner = CliRunner()
    env_file = tmp_path / ".env"
    backup_file = tmp_path / "config_backup.json"

    # Set up test environment
    env_content = """
    LOG_LEVEL=DEBUG
    DATABASE_URL=sqlite:///test.db
    """
    env_file.write_text(env_content.strip())

    # Test backup
    result = runner.invoke(
        config, ["backup", "--env-file", str(env_file), "--output", str(backup_file)]
    )
    assert result.exit_code == 0
    assert "Configuration backed up" in result.output
    assert backup_file.exists()

    # Verify backup content
    with open(backup_file) as f:
        backup_data = json.load(f)
        assert backup_data["LOG_LEVEL"] == "DEBUG"
        assert backup_data["DATABASE_URL"] == "sqlite:///test.db"

    # Clear environment
    env_file.unlink()

    # Test restore
    result = runner.invoke(
        config, ["restore", str(backup_file), "--env-file", str(env_file)]
    )
    assert result.exit_code == 0
    assert "Configuration restored" in result.output

    # Verify restored content
    assert env_file.exists()
    content = env_file.read_text()
    assert "LOG_LEVEL=DEBUG" in content
    assert "DATABASE_URL=sqlite:///test.db" in content


def test_config_validation(tmp_path: Path) -> None:
    """Test configuration validation."""
    runner = CliRunner()
    env_file = tmp_path / ".env"

    # Test invalid database URL
    result = runner.invoke(
        config, ["set", "DATABASE_URL", "invalid://url", "--env-file", str(env_file)]
    )
    assert result.exit_code == 0
    assert "Invalid value for DATABASE_URL" in result.output

    # Test invalid API key format
    result = runner.invoke(
        config, ["set", "OPENAI_API_KEY", "invalid-key", "--env-file", str(env_file)]
    )
    assert result.exit_code == 0
    assert "Invalid value for OPENAI_API_KEY" in result.output

    # Test invalid log level
    result = runner.invoke(
        config, ["set", "LOG_LEVEL", "INVALID", "--env-file", str(env_file)]
    )
    assert result.exit_code == 0
    assert "Invalid value for LOG_LEVEL" in result.output


def test_config_file_handling(tmp_path: Path) -> None:
    """Test configuration file handling edge cases."""
    runner = CliRunner()
    nonexistent_file = tmp_path / "nonexistent" / ".env"

    # Test non-existent file for get
    result = runner.invoke(config, ["get", "--env-file", str(nonexistent_file)])
    assert result.exit_code == 0
    assert "Environment file not found" in result.output

    # Test non-existent file for backup
    result = runner.invoke(config, ["backup", "--env-file", str(nonexistent_file)])
    assert result.exit_code == 0
    assert "Environment file not found" in result.output

    # Test non-existent backup file for restore
    result = runner.invoke(config, ["restore", str(nonexistent_file)])
    assert result.exit_code == 2  # Click's error code for file not found
    assert "does not exist" in result.output.lower()
