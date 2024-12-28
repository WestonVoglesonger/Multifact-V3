# System Narrative Compiler (SNC)

A tool for narrative-driven code generation that transforms natural language descriptions into functional code components.

## Installation

```bash
pip install snc
```

## Quick Start

1. Set up your environment variables in a `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
```

2. Create a simple script:

```python
from snc.application.services.ni_orchestrator import NIOrchestrator
from snc.infrastructure.repositories.setup import setup_repositories
from snc.infrastructure.services.setup import setup_services
from snc.infrastructure.llm.model_factory import OpenAIModelType

# Quick setup
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

# Create a narrative document
content = """
[Component:HelloWorld]
This component displays a simple greeting message.
It should show "Hello, World!" in a centered div with a blue background.
"""

# Create and compile
doc = orchestrator.create_ni_document(content, version="v1.0")
tokens = orchestrator.get_document_tokens(doc.id)
orchestrator.compile_tokens(tokens, OpenAIModelType.GPT_4O_MINI)
```

## Features

- Natural language to code transformation
- Component-based architecture
- Automatic dependency resolution
- Code validation and self-repair
- Support for multiple LLM providers

## Development Setup

1. Clone the repository
2. Install development dependencies:

```bash
pip install -e ".[dev]"
```

3. Run tests:

```bash
pytest
```

## Documentation

For detailed documentation, examples, and API reference, visit our [documentation site](https://snc.readthedocs.io/).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
