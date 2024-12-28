# NIOrchestrator

The NIOrchestrator is the main entry point for working with Multifact. It coordinates the parsing,
compilation, and management of narrative instructions.

```{eval-rst}
.. module:: backend.application.services.ni_orchestrator

.. autoclass:: NIOrchestrator
   :members:
   :undoc-members:
   :show-inheritance:
```

## Example Usage

Here's a basic example of using the NIOrchestrator:

```python
from multifact import NIOrchestrator

# Initialize the orchestrator
orchestrator = NIOrchestrator()

# Create a document with narrative instructions
doc = orchestrator.create_ni_document(
    initial_content="""
    [Scene:WelcomeScene]
    This scene welcomes users to the application.

    [Function:greet]
    This function displays a welcome message.
    """,
    version="v1"
)

# Get all tokens for the document
tokens = orchestrator.token_repo.get_all_tokens_for_document(doc.id)

# Compile tokens into artifacts
for token in tokens:
    artifact = orchestrator.compile_token(token.id)
    if artifact.valid:
        print(f"Successfully compiled {token.token_type}:{token.token_name}")
```

## Advanced Features

### Token Dependencies

The NIOrchestrator automatically handles token dependencies through reference tracking:

```python
# Create a document with dependencies
doc = orchestrator.create_ni_document(
    initial_content="""
    [Function:validateInput]
    This function validates user input.

    [Function:processForm]
    This function [REF:validateInput] processes the form after validation.
    """,
    version="v1"
)

# The orchestrator will ensure validateInput is compiled before processForm
```

### Self-Repair

If compilation fails, the orchestrator can attempt to repair invalid artifacts:

```python
# Enable self-repair
orchestrator.enable_self_repair = True

# The orchestrator will automatically attempt to fix invalid artifacts
artifact = orchestrator.compile_token(token_id)
if not artifact.valid:
    fixed_artifact = orchestrator.repair_artifact(artifact.id)
```

## Configuration

The orchestrator can be configured through environment variables or directly:

```python
from multifact.config import Settings

settings = Settings(
    MAX_COMPILATION_ATTEMPTS=5,
    ENABLE_ARTIFACT_CACHE=True
)
orchestrator = NIOrchestrator(settings=settings)
```

Note: We use the `eval-rst` directive in a fenced code block to maintain compatibility with Sphinx's autodoc features while using Markdown. This allows us to keep the automatic API documentation generation while using Markdown for the rest of the content.
