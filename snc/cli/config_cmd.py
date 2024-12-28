"""
Configuration management commands.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import click
from dotenv import load_dotenv, set_key, dotenv_values
from snc.config.validation import validate_config, ValidationResult


def mask_api_key(key: str) -> str:
    """Mask sensitive API key."""
    if len(key) <= 12:
        return key
    return f"{key[:10]}...{key[-4:]}"


@click.group()
def config() -> None:
    """Manage SNC configuration."""
    pass


@config.command()
@click.argument("key", required=False)
@click.argument("value", required=False)
@click.option("--env-file", default=".env", help="Path to .env file")
def set(key: Optional[str], value: Optional[str], env_file: str) -> None:
    """Set configuration value."""
    if not key or not value:
        click.echo("Usage: snc config set KEY VALUE")
        return

    # Validate the value
    result = validate_config({key: value})
    if key in result:
        validation = result[key]
        if not validation.is_valid:
            click.echo(f"❌ {validation.message}")
            return

    # Set the value
    try:
        set_key(env_file, key, value)
        click.echo(f"✅ Successfully set {key}")
    except Exception as e:
        click.echo(f"❌ Error setting {key}: {str(e)}")


@config.command()
@click.argument("key", required=False)
@click.option("--env-file", default=".env", help="Path to .env file")
def get(key: Optional[str], env_file: str) -> None:
    """Get configuration value(s)."""
    if not Path(env_file).exists():
        click.echo("❌ Environment file not found")
        return

    config_values = dotenv_values(env_file)
    if not config_values:
        click.echo("No configuration values found")
        return

    if key:
        if key not in config_values:
            click.echo("Key not found")
            return
        value = config_values[key]
        if "API_KEY" in key:
            value = mask_api_key(value)
        click.echo(f"{key}={value}")
    else:
        for k, v in config_values.items():
            if "API_KEY" in k:
                v = mask_api_key(v)
            click.echo(f"{k}={v}")


@config.command()
@click.option("--env-file", default=".env", help="Path to .env file")
@click.option("--output", default="config_backup.json", help="Output file path")
def backup(env_file: str, output: str) -> None:
    """Backup configuration to JSON file."""
    if not Path(env_file).exists():
        click.echo("❌ Environment file not found")
        return

    config_values = dotenv_values(env_file)
    if not config_values:
        click.echo("No configuration values to backup")
        return

    try:
        with open(output, "w") as f:
            json.dump(config_values, f, indent=2)
        click.echo(f"✅ Configuration backed up to {output}")
    except Exception as e:
        click.echo(f"❌ Error backing up configuration: {str(e)}")


@config.command()
@click.argument("backup_file")
@click.option("--env-file", default=".env", help="Path to .env file")
def restore(backup_file: str, env_file: str) -> None:
    """Restore configuration from JSON file."""
    try:
        with open(backup_file) as f:
            config_values = json.load(f)
    except Exception as e:
        click.echo(f"❌ Error reading backup file: {str(e)}")
        return

    # Validate all values
    validation_results = validate_config(config_values)
    has_errors = False
    for key, result in validation_results.items():
        if not result.is_valid:
            click.echo(f"❌ Invalid value for {key}: {result.message}")
            has_errors = True

    if has_errors:
        click.echo("❌ Restore aborted due to validation errors")
        return

    # Restore values
    try:
        for key, value in config_values.items():
            set_key(env_file, key, value)
        click.echo("✅ Configuration restored successfully")
    except Exception as e:
        click.echo(f"❌ Error restoring configuration: {str(e)}")


if __name__ == "__main__":
    config()
