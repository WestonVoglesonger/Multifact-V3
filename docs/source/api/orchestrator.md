# Orchestrator API

The `NIOrchestrator` (Narrative Interface Orchestrator) is the main entry point for the System Narrative Compiler. It handles the coordination between different components of the system.

## Basic Usage

```python
from snc import NIOrchestrator
from snc.config import Settings

# Initialize the orchestrator
settings = Settings()  # Load settings from environment
orchestrator = NIOrchestrator(settings)

# Compile a narrative to code
narrative = """
Create a function that calculates the factorial of a number recursively.
The function should be named 'factorial' and take one parameter 'n'.
"""

result = await orchestrator.compile_narrative(narrative)
print(result.code)
```

## API Reference

### NIOrchestrator

```python
class NIOrchestrator:
    """Main orchestrator for the System Narrative Compiler."""

    def __init__(self, settings: Settings):
        """Initialize the orchestrator.

        Args:
            settings: Configuration settings for the orchestrator
        """

    async def compile_narrative(
        self,
        narrative: str,
        context: Optional[Dict[str, Any]] = None,
        language: str = "python",
    ) -> CompilationResult:
        """Compile a natural language narrative into code.

        Args:
            narrative: The natural language description of the code to generate
            context: Optional context information for the compilation
            language: Target programming language (default: "python")

        Returns:
            CompilationResult containing the generated code and metadata

        Raises:
            CompilationError: If the narrative cannot be compiled
            ValidationError: If the generated code fails validation
        """

    async def validate_code(
        self,
        code: str,
        language: str = "python",
    ) -> ValidationResult:
        """Validate generated code against language-specific rules.

        Args:
            code: The code to validate
            language: Programming language of the code

        Returns:
            ValidationResult containing validation status and any errors
        """
```

## Examples

### Basic Code Generation

```python
# Generate a simple function
narrative = """
Create a function that reverses a string.
The function should be named 'reverse_string' and take one parameter 'text'.
"""

result = await orchestrator.compile_narrative(narrative)
print(result.code)
```

Output:
```python
def reverse_string(text: str) -> str:
    """Reverse the input string.

    Args:
        text: The string to reverse

    Returns:
        The reversed string
    """
    return text[::-1]
```

### Using Context

```python
# Generate code with additional context
context = {
    "existing_functions": ["calculate_tax", "apply_discount"],
    "required_imports": ["decimal"],
    "style": "functional",
}

narrative = """
Create a function that calculates the final price after tax and discount.
Use the existing calculate_tax and apply_discount functions.
"""

result = await orchestrator.compile_narrative(narrative, context=context)
print(result.code)
```

### Validation

```python
# Validate generated code
code = """
def calculate_sum(numbers):
    return sum(numbers)
"""

validation_result = await orchestrator.validate_code(code)
if validation_result.is_valid:
    print("Code passed validation!")
else:
    print("Validation errors:", validation_result.errors)
```

## Error Handling

The orchestrator provides detailed error information when things go wrong:

```python
from snc.exceptions import CompilationError, ValidationError

try:
    result = await orchestrator.compile_narrative("invalid narrative")
except CompilationError as e:
    print(f"Compilation failed: {e}")
    print(f"Error details: {e.details}")
except ValidationError as e:
    print(f"Validation failed: {e}")
    print(f"Error location: {e.location}")
```

## Best Practices

1. **Context Usage**: Always provide relevant context when available:
   - Existing functions and classes
   - Required imports
   - Coding style preferences
   - Project-specific requirements

2. **Error Handling**: Always handle potential exceptions:
   - CompilationError
   - ValidationError
   - ConnectionError (for LLM service issues)

3. **Validation**: Always validate generated code before using it:
   ```python
   result = await orchestrator.compile_narrative(narrative)
   validation = await orchestrator.validate_code(result.code)
   if not validation.is_valid:
       raise ValidationError(validation.errors)
   ```

4. **Resource Management**: The orchestrator manages its own resources, but it's good practice to close it when done:
   ```python
   try:
       result = await orchestrator.compile_narrative(narrative)
   finally:
       await orchestrator.close()
   ```
