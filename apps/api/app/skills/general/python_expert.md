# Python Expert

## Core Philosophy
Python is a language that values readability, simplicity, and elegance. Write code that is easy to understand, maintain, and debug.

## Best Practices

### Code Organization
- Use meaningful variable and function names
- Follow PEP 8 style guidelines
- Keep functions small and focused (single responsibility principle)
- Use list comprehensions and generator expressions when appropriate
- Leverage context managers for resource management

### Type Hints
```python
from typing import List, Optional, Callable

def process_items(items: List[str], callback: Callable[[str], int]) -> Optional[int]:
    """Process items and return total count."""
    if not items:
        return None
    return sum(callback(item) for item in items)
```

### Error Handling
```python
try:
    result = risky_operation()
except SpecificError as e:
    handle_error(e)
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### Virtual Environments
- Always use virtual environments (venv, conda, or poetry)
- Pin dependencies with exact versions for reproducibility
- Use `pip freeze` or `poetry lock` for lockfiles

## Performance Tips
1. Use built-in functions and standard library over manual implementations
2. Leverage `itertools` for efficient iteration
3. Use `functools.lru_cache` for memoization
4. Consider `numpy` for numerical operations
5. Profile before optimizing - use `cProfile` or `line_profiler`

## Testing with Python
```python
import pytest

def test_process_items_success():
    """Test successful item processing."""
    items = ["a", "b", "c"]
    result = process_items(items, len)
    assert result == 6
```

## Common Patterns
- **Strategy Pattern**: Use classes or functions for interchangeable algorithms
- **Decorator Pattern**: Use `@decorator` syntax for cross-cutting concerns
- **Context Managers**: Use `with` statements for resource cleanup
- **Factory Functions**: Use functions that return instances

## Security Considerations
- Never use `eval()` or `exec()` with user input
- Sanitize all inputs, especially file paths
- Use parameterized queries for database operations
- Keep dependencies updated to patch vulnerabilities

## Async Python
```python
import asyncio

async def fetch_data(url: str) -> dict:
    """Fetch data asynchronously."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def main():
    results = await asyncio.gather(
        fetch_data("https://api.example.com/1"),
        fetch_data("https://api.example.com/2"),
    )
    return results
```
