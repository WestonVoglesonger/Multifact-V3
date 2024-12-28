"""
CLI tool for initial SNC project setup.
"""

from typing import Optional
import os
import click
from pathlib import Path
import textwrap


@click.group()
def cli():
    """System Narrative Compiler (SNC) setup tools."""
    pass


@cli.command()
@click.option("--db-url", default="sqlite:///snc.db", help="Database URL", type=str)
@click.option("--openai-key", help="OpenAI API key", type=str)
@click.option("--groq-key", help="Groq API key", type=str)
def init(db_url: str, openai_key: Optional[str], groq_key: Optional[str]) -> None:
    """Initialize a new SNC project."""
    # Create project structure
    create_project_structure()

    # Create .env file
    create_env_file(db_url, openai_key, groq_key)

    # Create example file
    create_example_file()

    click.echo("✨ SNC project initialized successfully!")
    click.echo("\nNext steps:")
    click.echo("1. Review the .env file and update any missing values")
    click.echo("2. Check out examples/hello_world.py for a basic example")
    click.echo("3. Run 'snc validate' to verify your setup")


def create_project_structure() -> None:
    """Create the basic project structure."""
    dirs = ["examples", "artifacts", "logs"]
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        click.echo(f"📁 Created directory: {dir_name}")


def create_env_file(
    db_url: str, openai_key: Optional[str], groq_key: Optional[str]
) -> None:
    """Create the .env file with configuration."""
    env_content = textwrap.dedent(
        f"""
    # Database Configuration
    DATABASE_URL={db_url}

    # LLM Provider Configuration
    OPENAI_API_KEY={openai_key or 'your_openai_key_here'}
    GROQ_API_KEY={groq_key or 'your_groq_key_here'}

    # Logging Configuration
    LOG_LEVEL=INFO
    LOG_FILE=logs/snc.log
    """
    ).strip()

    with open(".env", "w") as f:
        f.write(env_content)
    click.echo("📝 Created .env file")


def create_example_file() -> None:
    """Create an example file."""
    example_content = textwrap.dedent(
        '''
    """
    Hello World example using SNC.
    """
    from snc.infrastructure.repositories.setup import setup_repositories
    from snc.infrastructure.services.setup import setup_services
    from snc.infrastructure.llm.model_factory import OpenAIModelType
    from snc.application.services.ni_orchestrator import NIOrchestrator

    def main() -> None:
        # Set up repositories and services
        session, repositories = setup_repositories()
        services = setup_services(session, repositories)
        
        # Initialize orchestrator
        orchestrator = NIOrchestrator(
            doc_repo=repositories.document_repo,
            token_repo=repositories.token_repo,
            artifact_repo=repositories.artifact_repo,
            llm_parser=services.llm_service,
            token_diff_service=services.token_diff_service,
            document_updater=services.document_updater,
            token_compiler=services.token_compiler,
            code_fixer_service=services.llm_service,
        )

        # Create a simple component
        content = """
        [Component:Greeting]
        Create a simple greeting component that displays 'Hello, World!'
        in a centered blue box with rounded corners.
        """
        
        # Generate and compile
        doc = orchestrator.create_ni_document(content, version="1.0")
        tokens = orchestrator.get_document_tokens(doc.id)
        orchestrator.compile_tokens(tokens, OpenAIModelType.GPT_4O_MINI)

    if __name__ == "__main__":
        main()
    '''
    ).strip()

    with open("examples/hello_world.py", "w") as f:
        f.write(example_content)
    click.echo("📝 Created example file: examples/hello_world.py")


if __name__ == "__main__":
    cli()
