Title: Project Style Guide

Purpose
Define consistent coding standards for Java and Python across formatting, naming, documentation, and code examples to ensure readability and maintainability.

2. Scope
Applies to all source code, tests, scripts, build files, and documentation in this repository.

3. Global conventions
- Comments: Prefer clear, actionable comments; avoid restating code. Explain intent, assumptions, and invariants.
- Logging: Use structured, leveled logging; no secrets or PII in logs. Include correlation IDs where available.
- Error handling: Fail fast on unrecoverable errors; wrap and preserve root causes; emit actionable messages.

4. Formatting
- Whitespace: No trailing spaces; Unix line endings; final newline in files.
- Line length: Target 100–120 chars; wrap thoughtfully.
- Imports: Group and sort; avoid unused; prefer explicit imports over wildcards.

5. Naming
- Files/Modules: Lowercase with hyphens or underscores; descriptive and concise.
- Classes/Types: PascalCase; nouns.
- Methods/Functions: camelCase; verbs.
- Constants: UPPER_SNAKE_CASE.
- Variables: camelCase; meaningful context.

6. Documentation
- Doc comments: Required on public APIs; include purpose, parameters, returns, exceptions, and examples.
- Readmes: Each module should have a README covering purpose, usage, and integration points.

7. Java-specific

- Language level: Java 21.
- Formatting: Use Spotless/Google Java Format; Checkstyle for rules.
- Nullability: Prefer Optional for return values; avoid nulls for collections; annotate with ‎`@Nullable` where applicable.
- Collections/streams: Prefer immutable views; avoid overly complex stream chains; consider readability.
- Exceptions: Checked for recoverable conditions; unchecked for programmer errors; custom exceptions per domain.
- Javadoc example:
```java
/**
 * Calculates discounted price for an order.
 *
 * @param order the order to price
 * @return the discounted total
 * @throws PricingException if pricing rules cannot be applied
 */
public Money price(Order order) { ... }
```

8. Python-specific

- Version: Python 3.12.
- Formatting: Black (line length 100), isort, ruff; mypy for types.
- Types: Mandatory type hints on public functions/classes; `from __future__ import annotations`.
- Errors: Raise specific exceptions; do not use bare `except`; include context.
- Docstrings (Google style):
```python
def price(order: Order) -> Money:
    """Calculate discounted price for an order.

    Args:
        order: The order to price.

    Returns:
        Discounted total.

    Raises:
        PricingError: If pricing rules cannot be applied.
    """
```
Async: Use `asyncio` for concurrent IO; no blocking calls in async functions.

9. Examples
- Java logging:
```java
log.info("Processing request {}", requestId);
```
- Python logging:
```python
logger.info("processing request %s", request_id)
```