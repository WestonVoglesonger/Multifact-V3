# Troubleshooting Guide

This guide helps you resolve common issues you might encounter while using SNC.

## Environment Setup Issues

### Missing API Keys

**Problem**: Error messages about missing or invalid API keys.

**Solution**:

1. Check that your `.env` file exists and contains the required API keys
2. Verify API key format:
   - OpenAI: Should start with `sk-`
   - Groq: Should start with `gsk_`
3. Use `snc validate` to verify your configuration

### Database Connection Issues

**Problem**: Cannot connect to database or database errors.

**Solution**:

1. For SQLite:
   - Ensure the database directory is writable
   - Check file permissions
2. For PostgreSQL:
   - Verify database credentials
   - Check if database server is running
   - Test connection with `psql`

## Code Generation Issues

### Invalid Token Errors

**Problem**: Errors about invalid tokens or compilation failures.

**Solution**:

1. Check token syntax in your narrative:
   - Tokens should be in format `[Type:Name]`
   - References should use `[REF:TokenName]`
2. Ensure token dependencies are correctly ordered
3. Review logs for detailed error messages

### Compilation Failures

**Problem**: Generated code fails to compile or has errors.

**Solution**:

1. Check the generated artifacts for syntax errors
2. Verify that all required dependencies are installed
3. Try running with a different LLM model
4. Use self-repair functionality:

```python
orchestrator.repair_artifact(artifact_id)
```

## Performance Issues

### Slow Generation

**Problem**: Code generation is taking too long.

**Solution**:

1. Use smaller, focused narratives
2. Enable caching:

```python
from snc.infrastructure.services.caching import enable_caching
enable_caching()
```

3. Consider using a faster LLM provider

### Memory Usage

**Problem**: High memory usage during generation.

**Solution**:

1. Process tokens in smaller batches
2. Clear cache periodically:

```python
from snc.infrastructure.services.caching import clear_cache
clear_cache()
```

3. Use SQLite instead of in-memory database

## Common Error Messages

### "Token compilation failed"

**Cause**: The LLM failed to generate valid code for a token.

**Solution**:

1. Make token description more specific
2. Check for circular dependencies
3. Try a different LLM model

### "Invalid artifact format"

**Cause**: Generated code doesn't match expected format.

**Solution**:

1. Check token type constraints
2. Verify narrative formatting
3. Use validation service to check output:

```python
validation_service.validate_artifact(artifact)
```

## Getting Help

If you're still experiencing issues:

1. Check the full documentation at https://snc.readthedocs.io/
2. Review the example projects in the `examples/` directory
3. Open an issue on GitHub with:
   - Full error message
   - Minimal reproduction case
   - Environment details (OS, Python version, etc.)
