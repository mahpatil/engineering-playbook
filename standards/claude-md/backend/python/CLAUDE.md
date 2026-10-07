# Python Backend Standards

Extends ../../CLAUDE.md.

## Runtime and tooling
- Python 3.13 for new services, 3.12 minimum. Pin in `.python-version` and `requires-python`.
- `uv` for environments and locking (`uv sync --locked`); no bare `pip` in CI or scripts.
- Approved stack: FastAPI, Pydantic v2 + pydantic-settings, SQLAlchemy 2 async + `asyncpg`, Alembic, `httpx`, `tenacity`, `structlog`, `PyJWT` (not `python-jose`), `pact-python`.
- Domain value objects: `@dataclass(frozen=True)`. Ports: `typing.Protocol`. API/config shapes: Pydantic.
- Blocking calls inside `async def` go through `asyncio.to_thread`; no `requests` in async services.

## Layout
```
src/<service>/{domain,application,infrastructure,api}/  config.py  errors.py  main.py
tests/{unit,integration,contract}/
```
`api/` holds `routers/`, `schemas/`, `dependencies.py`, `exception_handlers.py`; `infrastructure/` holds `postgres/`, `kafka/`, `http/`. Boundaries enforced by `import-linter`:
```toml
[tool.importlinter]
root_package = "<service>"
[[tool.importlinter.contracts]]
name = "layers"
type = "layers"
layers = ["<service>.api | <service>.infrastructure", "<service>.application", "<service>.domain"]
```

## FastAPI
- All handlers are `async def`; routers only translate and call a use case. Wire dependencies with `Depends`; one `@lru_cache` `get_config()`.
- Pydantic request models: `frozen=True`, constraints via `Field(...)`. Unknown fields rejected: `extra="forbid"`.
- `/health/live` (process up) and `/health/ready` (DB and broker reachable); `/metrics` via `prometheus-fastapi-instrumentator`.
- Register `RequestValidationError` handler so FastAPI's default 422 body becomes RFC 9457.
- Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`) via middleware.

### Error mapping
Hierarchy in `errors.py`: `ApplicationError` (carries `error_code`) with the subclasses below. Name the validation subclass `InputValidationError` to avoid clashing with `pydantic.ValidationError`.

| Error | Status |
|---|---|
| `NotFoundError` | 404 |
| `InputValidationError`, `RequestValidationError` | 422 |
| `BusinessRuleError`, state conflict | 409 |
| `ExternalServiceError` | 502 |
| anything else | 500, generic detail |

Handlers look up `type(exc)` in a dict and build the RFC 9457 body (see root) with `type=https://errors.<domain>/<error_code>`.

## Configuration
`pydantic_settings.BaseSettings` with `env_nested_delimiter="__"`; nested models per concern (`database`, `payments`). Env vars only; `.env` for local dev, never committed. Construct once at startup so missing values fail fast. Secrets typed as `SecretStr`.

## Persistence
- SQLAlchemy 2.0 `DeclarativeBase` + `Mapped[...]`, `async_sessionmaker`, `asyncpg`. ORM models stay in `infrastructure/postgres/`; repositories map to domain objects.
- Alembic migrations committed; never `create_all()` outside tests.

## Testing
- `pytest-asyncio` with `asyncio_mode = "auto"` (no `@pytest.mark.asyncio`). `respx` or `pytest-httpx` for outbound HTTP. `factory_boy` for data. `testcontainers` Postgres with real Alembic migrations.
- Provider contract verification with `pact-python` runs on every CI build.

## Observability
`structlog` JSON with `merge_contextvars`, `add_log_level`, `TimeStamper(fmt="iso")`, `JSONRenderer`; bind `service`, `trace_id`, `span_id`, `correlation_id` per request via contextvars (field names per root). OpenTelemetry: `opentelemetry-instrumentation-fastapi`, `-sqlalchemy`, `-httpx`.

## Resilience
`httpx.AsyncClient` with explicit timeouts. Retry only idempotent calls, on transport errors and 5xx:
```python
def _retryable(exc: BaseException) -> bool:
    return isinstance(exc, httpx.TransportError) or (
        isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500
    )

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), retry=retry_if_exception(_retryable))
async def get_payment(client: httpx.AsyncClient, payment_id: str) -> dict: ...
```
Non-idempotent POSTs retry only with an idempotency key.

## Enforcement (`pyproject.toml`)
```toml
[tool.ruff]
target-version = "py312"
line-length = 100
[tool.ruff.lint]
select = ["E","F","I","N","UP","ANN","S","B","A","C4","PT","T20","C90"]
[tool.ruff.lint.mccabe]
max-complexity = 10
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101","ANN"]
[tool.mypy]
python_version = "3.12"
strict = true
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
[tool.coverage.run]
branch = true
source = ["src"]
[tool.coverage.report]
fail_under = 80
```
CI, all required: `ruff check .`, `ruff format --check .`, `mypy src/`, `pytest --cov`, `pip-audit`, `lint-imports`.
Ruff rules cover mutable defaults (B006), bare `except` (E722), `print` (T20) and untyped signatures (ANN); `# type: ignore` needs an error code (`warn_unused_ignores` via strict).
