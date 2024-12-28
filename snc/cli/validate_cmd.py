"""
Configuration validation command.
"""

import os
import click
from dotenv import load_dotenv
from snc.config.validation import validate_config, ValidationResult


def print_validation_result(key: str, result: ValidationResult):
    """Print validation result with appropriate formatting."""
    if result.is_valid:
        click.echo(f"✅ {key}: {result.message}")
    else:
        click.echo(f"❌ {key}: {result.message}")


@click.command()
@click.option("--env-file", default=".env", help="Path to .env file")
def validate(env_file: str):
    """Validate SNC configuration."""
    if not os.path.exists(env_file):
        click.echo(f"❌ Environment file not found: {env_file}")
        return

    # Load environment variables
    load_dotenv(env_file)

    # Collect configuration
    config = {
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL"),
        "LOG_FILE": os.getenv("LOG_FILE"),
    }

    # Validate configuration
    results = validate_config(config)

    # Print results
    click.echo("\nValidating configuration...")
    click.echo("=" * 40)

    all_valid = True
    for key, result in results.items():
        print_validation_result(key, result)
        if not result.is_valid:
            all_valid = False

    click.echo("=" * 40)
    if all_valid:
        click.echo("\n✨ All configuration settings are valid!")
    else:
        click.echo("\n⚠️  Some configuration settings need attention.")
        click.echo("Please check the messages above and fix any issues.")
        click.echo("\nFor help, see:")
        click.echo("- Documentation: https://snc.readthedocs.io/")
        click.echo(
            "- Troubleshooting guide: https://snc.readthedocs.io/troubleshooting.html"
        )


if __name__ == "__main__":
    validate()
