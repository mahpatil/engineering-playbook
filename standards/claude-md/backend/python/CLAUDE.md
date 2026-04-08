# Python Backend Standards

Read `../../CLAUDE.md` first. This file extends those principles for Python services built with FastAPI.

---

## Language & Runtime

- **Python 3.12+** is the minimum. Python 3.13 is preferred for new services.
- Pin the Python version in `.python-version` (pyenv) and in `pyproject.toml`.
- Use `uv` for dependency management and virtual environments. Do not use `pip` directly in CI or scripts.

```toml
# pyproject.toml
[project]
name = "order-service"
requires-python = ">=3.12"
```

```
# .python-version
3.12
```

### Use These Python Features

| Feature | When to use |
|---|---|
| Type hints (PEP 484) | All function signatures and class attributes — mandatory |
| Dataclasses / `@dataclass` | Immutable value objects and DTOs with `frozen=True` |
| Pydantic `BaseModel` | API request/response shapes and configuration |
| `Enum` | Finite domain states (`OrderStatus`, `Currency`) |
| `typing.Protocol` | Port (interface) definitions in the application layer |
| `async`/`await` | All I/O-bound operations — use `asyncio` + `anyio` |
| Pattern matching (`match`) | Dispatching on domain result types and enum variants (Python 3.10+) |
| `__slots__` | High-volume value objects where memory matters |

```python
# GOOD — frozen dataclass as value object
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class Currency(str, Enum):
    GBP = "GBP"
    USD = "USD"
    EUR = "EUR"

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValueError("Money amount cannot be negative")

# GOOD — Protocol as port (interface)
from typing import Protocol

class OrderRepository(Protocol):
    async def find_by_id(self, order_id: OrderId) -> Order | None: ...
    async def save(self, order: Order) -> None: ...

# GOOD — match on result type
match result:
    case OrderResult.Created(order=order):
        return JSONResponse(status_code=201, content=order_to_dto(order))
    case OrderResult.Rejected(reason=reason):
        raise BusinessRuleError(reason)
```

### Avoid These

- Mutable default arguments (`def f(items=[]):`). Use `None` with a guard.
- `type: ignore` comments without a specific error code and brief explanation.
- `Any` in public function signatures. Use proper types or `TypeVar`.
- `global` and `nonlocal` in application code.
- Bare `except:` or `except Exception:` without logging and re-raising or a documented reason.
- Synchronous I/O (blocking `requests`, blocking file reads) inside `async` functions. Use `httpx.AsyncClient`, `aiofiles`, or `asyncio.to_thread`.

---

## Project Structure

```
src/
  <service_name>/
    domain/           # Entities, value objects, domain events — no framework imports
      __init__.py
      order.py        # Aggregate root
      order_id.py     # Value object
      money.py        # Value object
      events.py       # Domain events
    application/      # Use cases, port Protocols, application services
      __init__.py
      ports.py        # Repository and service Protocols
      confirm_order.py
    infrastructure/   # Adapters: Postgres, Kafka, HTTP clients
      __init__.py
      postgres/
      kafka/
      http/
    api/              # FastAPI routers, request/response schemas, exception handlers
      __init__.py
      routers/
      schemas/
      exception_handlers.py
    config.py         # Pydantic Settings configuration
    errors.py         # Application error hierarchy
    main.py
tests/
  unit/
  integration/
  contract/
pyproject.toml
```

Domain modules must not import from `infrastructure` or `api`. Application modules must not import from `infrastructure`. Enforce with `import-linter`.

---

## Web Framework (FastAPI)

- **FastAPI 0.110+** is the standard HTTP framework.
- Use `async def` for all route handlers. No `def` (synchronous) handlers — use `asyncio.to_thread` or a thread pool executor for blocking calls.
- Routers are thin orchestrators — dispatch immediately to the application layer.

```python
# api/routers/orders.py
from fastapi import APIRouter, Depends, status
from ..schemas.orders import CreateOrderRequest, OrderResponse
from ...application.create_order import CreateOrderUseCase
from ..dependencies import get_order_service

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    service: CreateOrderUseCase = Depends(get_order_service),
) -> OrderResponse:
    result = await service.execute(request.to_command())
    match result:
        case OrderResult.Created(order=order):
            return OrderResponse.from_domain(order)
        case OrderResult.Rejected(reason=reason):
            raise BusinessRuleError(reason)
```

### Request/Response Schemas

```python
# api/schemas/orders.py
from pydantic import BaseModel, Field
from uuid import UUID

class CreateOrderRequest(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=36)
    items: list[OrderLineItemRequest] = Field(..., min_length=1)
    currency: str = Field(..., pattern="^[A-Z]{3}$")

    model_config = {"frozen": True}

    def to_command(self) -> CreateOrderCommand:
        return CreateOrderCommand(
            customer_id=CustomerId(self.customer_id),
            items=[item.to_domain() for item in self.items],
            currency=Currency(self.currency),
        )
```

### Exception Handlers

```python
# api/exception_handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse

async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    status_map = {
        NotFoundError: 404,
        ValidationError: 422,
        BusinessRuleError: 409,
        ExternalServiceError: 502,
    }
    status_code = status_map.get(type(exc), 500)
    detail = str(exc) if status_code < 500 else "An unexpected error occurred"

    return JSONResponse(
        status_code=status_code,
        content={
            "type": f"https://errors.example.com/{exc.error_code}",
            "title": exc.__class__.__name__,
            "status": status_code,
            "detail": detail,
            "correlationId": request.state.correlation_id,
        },
    )
```

---

## Configuration (Pydantic Settings)

```python
# config.py
from pydantic import Field, PostgresDsn, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseConfig(BaseSettings):
    url: PostgresDsn
    max_connections: int = Field(default=10, ge=1)
    min_connections: int = Field(default=2, ge=1)

class PaymentsConfig(BaseSettings):
    provider_url: AnyHttpUrl
    timeout_seconds: int = Field(default=10, ge=1)
    max_retries: int = Field(default=3, ge=0)

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    database: DatabaseConfig
    payments: PaymentsConfig
    log_level: str = "INFO"
```

- All configuration is loaded from environment variables. No secrets in `.env` files committed to source control.
- Validate on startup with `model_validate`. Fail fast with clear error messages.

---

## Error Handling

```python
# errors.py
class ApplicationError(Exception):
    error_code: str = "application-error"

class NotFoundError(ApplicationError):
    error_code = "not-found"

class ValidationError(ApplicationError):
    error_code = "validation-failed"

class BusinessRuleError(ApplicationError):
    error_code = "business-rule-violation"

class ExternalServiceError(ApplicationError):
    error_code = "external-service-error"
```

### Rules

- Never use bare `except:`. Catch specific exception types.
- Domain errors are typed exception subclasses, not plain strings or generic `Exception`.
- Log errors at the boundary (HTTP handler or message consumer). Do not log inside domain or application layers.
- Internal error details (DB errors, stack traces) must never reach API responses in production.

---

## Dependency Injection

- Use **FastAPI's built-in dependency injection** (`Depends`) for HTTP handlers.
- For application services, use constructor injection. Do not use service locators or module-level globals.

```python
# api/dependencies.py
from functools import lru_cache
from ..config import AppConfig
from ..infrastructure.postgres import PostgresOrderRepository
from ..application.confirm_order import ConfirmOrderUseCase

@lru_cache
def get_config() -> AppConfig:
    return AppConfig()

async def get_order_repository(config: AppConfig = Depends(get_config)) -> OrderRepository:
    return PostgresOrderRepository(dsn=str(config.database.url))

async def get_confirm_order_use_case(
    repo: OrderRepository = Depends(get_order_repository),
) -> ConfirmOrderUseCase:
    return ConfirmOrderUseCase(repository=repo)
```

---

## Persistence (SQLAlchemy + Alembic)

- **SQLAlchemy 2.0+** (async) for database access. Use the `asyncio` extension with `asyncpg` driver.
- **Alembic** for migrations. Migration files are committed to source control. Never use `create_all()` in production.
- SQLAlchemy ORM models live in `infrastructure/`. They are never exposed to the domain or API layers.
- Map ORM models to domain objects at the repository boundary.

```python
# infrastructure/postgres/models.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Numeric, DateTime
import uuid

class Base(DeclarativeBase):
    pass

class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

# infrastructure/postgres/order_repository.py
class PostgresOrderRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def find_by_id(self, order_id: OrderId) -> Order | None:
        async with self._session_factory() as session:
            model = await session.get(OrderModel, order_id.value)
            return OrderMapper.to_domain(model) if model else None
```

### Query Performance

- Review `EXPLAIN ANALYZE` output for all non-trivial queries during code review.
- Add indexes for all foreign keys and frequently filtered columns.
- Paginate all list queries. Never return unbounded result sets.

---

## Testing

### Unit Tests (pytest)

```python
# tests/unit/test_confirm_order.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.confirm_order import ConfirmOrderUseCase

@pytest.mark.asyncio
async def test_confirm_order_publishes_event_when_pending():
    mock_repo = AsyncMock()
    mock_events = AsyncMock()
    order = Order.pending(OrderId.new(), CustomerId.new())
    mock_repo.find_by_id.return_value = order

    use_case = ConfirmOrderUseCase(repository=mock_repo, events=mock_events)
    result = await use_case.execute(ConfirmOrderCommand(order.id, "txn-123"))

    assert isinstance(result, OrderResult.Created)
    mock_events.publish.assert_called_once()
    published_event = mock_events.publish.call_args[0][0]
    assert isinstance(published_event, OrderConfirmedEvent)
```

### Integration Tests (pytest + Testcontainers)

```python
# tests/integration/test_order_repository.py
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="module")
async def postgres():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg

@pytest.mark.asyncio
async def test_save_and_find_order_roundtrip(postgres):
    pool = await create_pool(postgres.get_connection_url())
    await run_migrations(pool)
    repo = PostgresOrderRepository(pool)

    order = Order.pending(OrderId.new(), CustomerId.new())
    await repo.save(order)
    found = await repo.find_by_id(order.id)

    assert found == order
```

- Use `pytest-asyncio` for async tests. Set `asyncio_mode = "auto"` in `pyproject.toml`.
- Use `pytest-httpx` or `respx` for mocking outbound HTTP calls. Never mock at the socket level.
- Do not use SQLite as a substitute for Postgres in tests.
- Use `factory_boy` for test data generation.

### Contract Tests (Pact)

- Use `pact-python` for consumer-driven contract tests.
- Provider verification runs in CI on every build.

---

## Structured Logging and Observability

- Use `structlog` for structured JSON logging. No `print()` or `logging.basicConfig` in production code.
- Add `trace_id`, `correlation_id`, and `service` to every log event.

```python
# main.py
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

# usage
logger = structlog.get_logger()
logger.info("order_confirmed", order_id=str(order_id), customer_id=str(customer_id))
```

- Use `opentelemetry-sdk` with `opentelemetry-instrumentation-fastapi` and `opentelemetry-instrumentation-sqlalchemy`.
- Expose Prometheus metrics via `/metrics` using `prometheus-fastapi-instrumentator`.
- Every service exposes `/health/live` and `/health/ready` endpoints.

---

## Resilience

- Use `tenacity` for retry logic on external service calls. Configure only for idempotent operations.
- Use `httpx` with configured timeouts for all outbound HTTP calls. Never use `requests` in async services.

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.TransientError),
)
async def call_payments_api(client: httpx.AsyncClient, payload: dict) -> dict:
    response = await client.post("/payments", json=payload, timeout=10.0)
    response.raise_for_status()
    return response.json()
```

---

## Build and Tooling

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 100
select = ["E", "F", "I", "N", "UP", "ANN", "S", "B", "A", "C4", "PT"]
ignore = ["ANN101", "ANN102"]

[tool.ruff.per-file-ignores]
"tests/**" = ["S101", "ANN"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = false

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
fail_under = 80
```

Required CI checks (all must pass):
1. `ruff check .` — linting
2. `ruff format --check .` — formatting
3. `mypy src/` — type checking
4. `pytest --cov=src --cov-fail-under=80` — tests with coverage
5. `pip-audit` — dependency vulnerability scan

---

## Security

- Run `pip-audit` in CI. Block on HIGH or CRITICAL vulnerabilities.
- Validate all input at API boundaries using Pydantic. Never pass raw request data to domain objects.
- Use `python-jose` or `PyJWT` for JWT validation. Never implement JWT parsing manually.
- **Never log PII** — review `structlog` `bind` calls carefully.
- Use `python-decouple` or Pydantic Settings for secrets — never `os.environ.get("SECRET")` inline.
- Set `X-Content-Type-Options`, `X-Frame-Options`, and `Content-Security-Policy` headers via middleware.

---

## Related Standards

- `../../CLAUDE.md` — Root engineering principles
- `../../api/CLAUDE.md` — API design (routers, schemas, versioning)
- `standards/overall/tech-stack.md` — Approved Python libraries and frameworks
- `standards/detailed/microservices.md` — Microservice decomposition principles
