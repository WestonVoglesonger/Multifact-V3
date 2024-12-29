# Version Compatibility

This document outlines the compatibility matrix for System Narrative Compiler with various dependencies and systems.

## Python Version Compatibility

SNC is tested and supported on the following Python versions:
- Python 3.8
- Python 3.9
- Python 3.10

## Operating System Compatibility

SNC is platform-independent and tested on:
- Linux (Ubuntu 20.04+, Debian 10+)
- macOS (10.15+)
- Windows 10/11 with WSL2

## Major Dependencies Version Matrix

| SNC Version | FastAPI | SQLAlchemy | Pydantic | OpenAI | Groq |
|------------|---------|------------|-----------|---------|------|
| 0.1.0      | 0.100.0 | 2.0.4      | 1.8.0+    | 1.57.4  | 0.13.1 |

## Database Compatibility

The following databases are supported:
- PostgreSQL 12+
- SQLite 3.30+

## LLM Provider Compatibility

SNC is tested with the following LLM providers:
- OpenAI (GPT-3.5, GPT-4)
- Groq (LLaMA2, Mixtral)

## Breaking Changes

### Version 0.1.0
- Initial release, no breaking changes

## Future Compatibility Guarantees

We follow these principles for version compatibility:
1. Minor version updates (0.x.0) may include new features but maintain backward compatibility
2. Patch updates (0.0.x) only include bug fixes and maintain backward compatibility
3. Major version updates (x.0.0) may include breaking changes, which will be clearly documented

## Migration Guides

### Upgrading to 0.1.0
- Initial release, no migration needed

## Known Compatibility Issues

### FastAPI
- When using FastAPI >0.101.0, you may need to update your dependency injection patterns

### SQLAlchemy
- SQLAlchemy 2.0.4+ is required for proper async support
- Earlier versions are not supported due to API changes

### OpenAI
- OpenAI SDK version 1.57.4 is required for proper streaming support
- Earlier versions may work but are not officially supported
