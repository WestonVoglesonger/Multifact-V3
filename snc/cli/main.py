"""
Main CLI module for SNC.
"""

import click
from snc.cli.setup_cmd import init
from snc.cli.validate_cmd import validate
from snc.cli.config_cmd import config
from snc.script.repl import main as repl


@click.group()
def cli():
    """System Narrative Compiler (SNC) command line interface."""
    pass


# Add commands
cli.add_command(init, name="init")
cli.add_command(validate, name="validate")
cli.add_command(repl, name="repl")
cli.add_command(config, name="config")


@cli.command()
def version():
    """Show SNC version information."""
    import pkg_resources

    version = pkg_resources.get_distribution("snc").version
    click.echo(f"SNC version {version}")


@cli.command()
@click.argument("token_type", required=False)
def list_tokens(token_type: str = None):
    """List available token types and their descriptions."""
    tokens = {
        "Component": "UI components (e.g., buttons, forms, layouts)",
        "Scene": "Complete page or view layouts",
        "Function": "Reusable functions and utilities",
        "Style": "CSS styles and themes",
        "Test": "Unit and integration tests",
        "Model": "Data models and schemas",
        "API": "API endpoints and handlers",
    }

    if token_type:
        if token_type in tokens:
            click.echo(f"\n{token_type}:")
            click.echo("-" * (len(token_type) + 1))
            click.echo(tokens[token_type])
        else:
            click.echo(f"Unknown token type: {token_type}")
            click.echo("\nAvailable token types:")
            for t in tokens:
                click.echo(f"- {t}")
    else:
        click.echo("\nAvailable token types:")
        for t, desc in tokens.items():
            click.echo(f"\n{t}:")
            click.echo("-" * (len(t) + 1))
            click.echo(desc)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def analyze(path: str):
    """Analyze a narrative document for potential issues."""
    from snc.infrastructure.repositories.setup import setup_repositories
    from snc.infrastructure.services.setup import setup_services

    # Set up basic services
    session, repositories = setup_repositories()
    services = setup_services(session, repositories)

    try:
        with open(path, "r") as f:
            content = f.read()

        # Basic checks
        issues = []

        # Check token syntax
        import re

        tokens = re.findall(r"\[(.*?)\]", content)
        for token in tokens:
            if ":" not in token and token != "REF":
                issues.append(f"Invalid token format: [{token}]. Should be [Type:Name]")

        # Check references
        refs = re.findall(r"\[REF:(.*?)\]", content)
        defined_tokens = re.findall(r"\[(?!REF:)(.*?):(.*?)\]", content)
        defined_names = [name for _, name in defined_tokens]

        for ref in refs:
            if ref not in defined_names:
                issues.append(f"Reference to undefined token: {ref}")

        # Report results
        if issues:
            click.echo("\n⚠️  Found potential issues:")
            for issue in issues:
                click.echo(f"- {issue}")
        else:
            click.echo("\n✅ No issues found in the narrative.")

    except Exception as e:
        click.echo(f"\n❌ Error analyzing file: {str(e)}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", type=click.Choice(["text", "json", "dot"]), default="text")
def dependencies(path: str, format: str):
    """Analyze and display token dependencies."""
    from snc.infrastructure.repositories.setup import setup_repositories
    from snc.infrastructure.services.setup import setup_services
    import json

    try:
        with open(path, "r") as f:
            content = f.read()

        # Extract tokens and dependencies
        import re

        tokens = re.findall(r"\[(?!REF:)(.*?):(.*?)\]", content)
        refs = re.findall(r"\[REF:(.*?)\]", content)

        # Build dependency graph
        graph = {}
        current_token = None
        for line in content.split("\n"):
            token_match = re.search(r"\[(?!REF:)(.*?):(.*?)\]", line)
            if token_match:
                current_token = token_match.group(2)
                graph[current_token] = []
            elif current_token and "[REF:" in line:
                refs = re.findall(r"\[REF:(.*?)\]", line)
                graph[current_token].extend(refs)

        # Output based on format
        if format == "text":
            for token, deps in graph.items():
                click.echo(f"\n{token}:")
                if deps:
                    for dep in deps:
                        click.echo(f"  ├─ {dep}")
                else:
                    click.echo("  └─ (no dependencies)")

        elif format == "json":
            click.echo(json.dumps(graph, indent=2))

        elif format == "dot":
            click.echo("digraph G {")
            for token, deps in graph.items():
                for dep in deps:
                    click.echo(f'  "{token}" -> "{dep}";')
            click.echo("}")

    except Exception as e:
        click.echo(f"\n❌ Error analyzing dependencies: {str(e)}")


if __name__ == "__main__":
    cli()
