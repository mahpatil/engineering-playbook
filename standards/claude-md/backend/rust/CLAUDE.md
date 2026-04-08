# Rust Backend Standards

Read `../../CLAUDE.md` first. This file extends those principles for Rust services.

---

## Language & Runtime

- **Rust 1.90+** (stable channel). Pin the toolchain version in `rust-toolchain.toml`.
- Use the latest stable Rust. Nightly is only permitted for benchmark harnesses, never production code.
- Enable `#![deny(warnings)]` in `lib.rs` / `main.rs`. Warnings are errors in CI.

```toml
# rust-toolchain.toml
[toolchain]
channel = "1.80"
components = ["rustfmt", "clippy"]
```

### Use These Rust Features

| Feature | When to use |
|---|---|
| `Result<T, E>` | All fallible operations — never `unwrap`/`expect` in production code paths |
| `Option<T>` | Optional values — never use sentinel values like `-1` or empty strings |
| `?` operator | Propagating errors up the call stack |
| `impl Trait` | Return types for iterators, futures, and closures where concrete type is not needed |
| `async/await` | All I/O-bound operations — use `tokio` as the async runtime |
| Enums with data | Domain result types, error hierarchies, discriminated unions |
| Newtype pattern | Typed IDs and value objects (`struct OrderId(Uuid)`) |
| Derive macros | `Debug`, `Clone`, `PartialEq`, `serde::Serialize/Deserialize` on data types |

```rust
// GOOD — newtype for domain identity
#[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct OrderId(uuid::Uuid);

impl OrderId {
    pub fn new() -> Self {
        Self(uuid::Uuid::new_v4())
    }
}

// GOOD — enum result type for domain outcomes
pub enum OrderResult {
    Created(Order),
    Rejected { reason: String },
}

// GOOD — error propagation with ?
pub async fn confirm_order(
    id: OrderId,
    payment: PaymentConfirmation,
    repo: &dyn OrderRepository,
) -> Result<OrderResult, ApplicationError> {
    let mut order = repo.find_by_id(&id).await?
        .ok_or(ApplicationError::NotFound(id.to_string()))?;
    let result = order.confirm(payment)?;
    repo.save(&order).await?;
    Ok(result)
}
```

### Avoid These

- `unwrap()` and `expect()` outside of tests and startup validation. Use `?` or explicit error handling.
- `clone()` for performance-critical paths. Prefer borrowing; profile before cloning.
- `Mutex<T>` where `RwLock<T>` or message passing suffices.
- `Box<dyn Error>` as a function return type in library code. Use typed error enums.
- `unsafe` code without a `// SAFETY:` comment explaining the invariant being upheld and a code review from a senior engineer.
- Blocking calls inside `async` functions. Use `tokio::task::spawn_blocking` for CPU-bound work.

---

## Project Structure

Follow a layered structure matching the root standard:

```
src/
  domain/           # Entities, value objects, domain events — no framework dependencies
    mod.rs
    order.rs        # Aggregate root
    order_id.rs     # Value object
    money.rs        # Value object
    events.rs       # Domain events
  application/      # Use cases, port traits, application services
    mod.rs
    ports.rs        # Repository and service traits
    confirm_order.rs
  infrastructure/   # Adapters: Postgres, Kafka, HTTP clients
    mod.rs
    postgres/
    kafka/
    http/
  api/              # Axum handlers, request/response DTOs, OpenAPI
    mod.rs
    handlers/
    dto/
  config.rs         # Configuration structs
  error.rs          # Application error hierarchy
  main.rs
tests/
  integration/
  contract/
```

Enforce dependency rules with `cargo-depcheck` or module visibility (`pub(crate)`, `pub(super)`). Domain modules must not `use` infrastructure or API modules.

---

## Web Framework (Axum)

- **Axum 0.7+** is the standard HTTP framework.
- Use `tower` and `tower-http` for middleware: tracing, CORS, compression, request ID.
- Route handlers are thin — dispatch to application layer immediately.

```rust
// routes.rs
pub fn order_routes() -> Router<AppState> {
    Router::new()
        .route("/orders", post(create_order))
        .route("/orders/:id/confirm", post(confirm_order))
        .route("/orders/:id", get(get_order))
}

// handlers/orders.rs
pub async fn create_order(
    State(state): State<AppState>,
    Json(cmd): Json<CreateOrderCommand>,
) -> Result<(StatusCode, Json<OrderDto>), AppError> {
    let result = state.order_service.create(cmd).await?;
    match result {
        OrderResult::Created(order) => Ok((StatusCode::CREATED, Json(OrderDto::from(order)))),
        OrderResult::Rejected { reason } => Err(AppError::BusinessRule(reason)),
    }
}
```

### Middleware Stack

```rust
// main.rs
let app = Router::new()
    .merge(order_routes())
    .layer(
        ServiceBuilder::new()
            .layer(TraceLayer::new_for_http())
            .layer(RequestIdLayer::new())
            .layer(CorsLayer::permissive())  // tighten for production
            .layer(CompressionLayer::new()),
    );
```

---

## Configuration

- Use `config` crate with `serde`. All configuration is typed; no raw string lookups.
- Load from environment variables in production. File-based config for local dev only.
- **No secrets in config files or source.** Reference via environment variables populated by the secrets manager.
- Validate configuration at startup. Fail fast with a meaningful error if required values are missing.

```rust
#[derive(Debug, serde::Deserialize)]
pub struct AppConfig {
    pub server: ServerConfig,
    pub database: DatabaseConfig,
    pub payments: PaymentsConfig,
}

#[derive(Debug, serde::Deserialize)]
pub struct DatabaseConfig {
    pub url: String,      // injected from DATABASE_URL env var
    pub max_connections: u32,
    pub min_connections: u32,
}

#[derive(Debug, serde::Deserialize)]
pub struct PaymentsConfig {
    pub provider_url: String,  // injected from PAYMENTS_PROVIDER_URL env var
    pub timeout_secs: u64,
    pub max_retries: u32,
}
```

---

## Error Handling

Define a typed application error hierarchy using `thiserror`:

```rust
// error.rs
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ApplicationError {
    #[error("Entity not found: {0}")]
    NotFound(String),

    #[error("Validation failed: {0}")]
    Validation(String),

    #[error("Business rule violation: {0}")]
    BusinessRule(String),

    #[error("External service error: {0}")]
    ExternalService(#[from] reqwest::Error),

    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
}

// Map to HTTP responses
impl IntoResponse for ApplicationError {
    fn into_response(self) -> Response {
        let (status, detail) = match &self {
            ApplicationError::NotFound(_)     => (StatusCode::NOT_FOUND, self.to_string()),
            ApplicationError::Validation(_)   => (StatusCode::UNPROCESSABLE_ENTITY, self.to_string()),
            ApplicationError::BusinessRule(_) => (StatusCode::CONFLICT, self.to_string()),
            ApplicationError::ExternalService(_) => (StatusCode::BAD_GATEWAY, "External service error".to_string()),
            ApplicationError::Database(_)     => (StatusCode::INTERNAL_SERVER_ERROR, "An unexpected error occurred".to_string()),
        };
        let body = Json(ProblemDetail::new(status.as_u16(), detail));
        (status, body).into_response()
    }
}
```

### Rules

- Never `unwrap()` or `expect()` in application code paths. Use `?` or explicit `match`.
- Domain errors are typed enum variants, not strings.
- Log errors at the boundary (HTTP handler or message consumer), not inside domain or application layers.
- Internal error details (DB errors, stack traces) must never reach API responses.

---

## Persistence (SQLx)

- **SQLx 0.7+** for async database access. Prefer compile-time checked queries (`sqlx::query_as!`).
- Migrations via `sqlx-cli`. Migration files are committed to source control.
- Never use an ORM that maps database rows directly to domain objects. Map at the repository boundary.
- Repository traits are defined in `application/ports.rs`, implementations live in `infrastructure/`.

```rust
// application/ports.rs
#[async_trait::async_trait]
pub trait OrderRepository: Send + Sync {
    async fn find_by_id(&self, id: &OrderId) -> Result<Option<Order>, ApplicationError>;
    async fn save(&self, order: &Order) -> Result<(), ApplicationError>;
    async fn find_active_by_customer(&self, customer_id: &CustomerId) -> Result<Vec<Order>, ApplicationError>;
}

// infrastructure/postgres/order_repository.rs
pub struct PostgresOrderRepository {
    pool: sqlx::PgPool,
}

#[async_trait::async_trait]
impl OrderRepository for PostgresOrderRepository {
    async fn find_by_id(&self, id: &OrderId) -> Result<Option<Order>, ApplicationError> {
        let row = sqlx::query_as!(
            OrderRow,
            "SELECT id, customer_id, status, created_at FROM orders WHERE id = $1",
            id.as_uuid()
        )
        .fetch_optional(&self.pool)
        .await?;
        Ok(row.map(Order::from))
    }
}
```

### Query Performance

- Review `EXPLAIN ANALYZE` output for all non-trivial queries during code review.
- Add indexes for all foreign keys and frequently filtered columns.
- Paginate all list queries. Never return unbounded result sets.
- Use connection pooling via `sqlx::PgPool`. Configure pool sizes based on load testing.

---

## Testing

### Unit Tests

- Test domain logic and application services without any I/O.
- Use `mockall` to generate mock implementations of port traits.
- Tests live in the same file as the code under test (`#[cfg(test)]` module) for unit tests.

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use mockall::predicate::*;

    #[tokio::test]
    async fn confirm_order_publishes_event_when_pending() {
        let mut mock_repo = MockOrderRepository::new();
        let order = Order::pending(OrderId::new(), CustomerId::new());
        let order_id = order.id().clone();

        mock_repo
            .expect_find_by_id()
            .with(eq(order_id.clone()))
            .returning(move |_| Ok(Some(order.clone())));
        mock_repo.expect_save().returning(|_| Ok(()));

        let mut mock_events = MockEventPublisher::new();
        mock_events
            .expect_publish()
            .withf(|e| matches!(e, DomainEvent::OrderConfirmed(_)))
            .returning(|_| Ok(()));

        let result = confirm_order(order_id, valid_payment(), &mock_repo, &mock_events)
            .await
            .unwrap();

        assert!(matches!(result, OrderResult::Created(_)));
    }
}
```

### Integration Tests

- Use Testcontainers (`testcontainers` crate) for database tests. Never use SQLite as a substitute for Postgres.
- Integration tests live in `tests/integration/`.
- Use `tokio::test` for async tests.

```rust
// tests/integration/order_repository_test.rs
use testcontainers::{clients::Cli, images::postgres::Postgres};

#[tokio::test]
async fn save_and_find_order_roundtrip() {
    let docker = Cli::default();
    let postgres = docker.run(Postgres::default());
    let pool = create_pool(&postgres.get_host_port_ipv4(5432)).await;

    sqlx::migrate!("./migrations").run(&pool).await.unwrap();

    let repo = PostgresOrderRepository::new(pool);
    let order = Order::pending(OrderId::new(), CustomerId::new());

    repo.save(&order).await.unwrap();
    let found = repo.find_by_id(order.id()).await.unwrap();

    assert_eq!(Some(order), found);
}
```

### Contract Tests (Pact)

- Every service that consumes an API writes Pact consumer tests using `pact_consumer`.
- Provider verification runs in CI on every build.

---

## Async Runtime (Tokio)

- **Tokio** is the only approved async runtime. Do not mix runtimes.
- Use `tokio::spawn` for independent concurrent tasks. Propagate errors via `JoinHandle`.
- For CPU-bound work inside async context, use `tokio::task::spawn_blocking`.
- Configure the multi-threaded runtime in `main.rs`:

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    init_tracing();
    let config = AppConfig::from_env()?;
    let state = AppState::new(&config).await?;
    let app = build_router(state);

    let listener = tokio::net::TcpListener::bind(&config.server.bind_addr).await?;
    tracing::info!("Listening on {}", config.server.bind_addr);
    axum::serve(listener, app).await?;
    Ok(())
}
```

---

## Resilience

- Use `tower`'s `retry` and `timeout` middleware for HTTP client calls.
- Use the `circuit_breaker` pattern from `tower` or `failsafe` crate for external service calls.
- Configure retries only for **idempotent** operations.

```rust
let client = reqwest::Client::builder()
    .timeout(Duration::from_secs(config.payments.timeout_secs))
    .build()?;

// Wrap in retry with exponential backoff for idempotent calls
let response = retry(ExponentialBackoff::default(), || async {
    client.get(&url).send().await.map_err(|e| backoff::Error::transient(e))
})
.await?;
```

---

## Structured Logging and Observability

- Use `tracing` crate with `tracing-subscriber`. Output JSON in deployed environments.
- Instrument all async functions and important synchronous code paths with `#[tracing::instrument]`.
- Add `traceId`, `correlationId`, `service` fields to every span.

```rust
// main.rs — tracing setup
fn init_tracing() {
    tracing_subscriber::fmt()
        .json()
        .with_current_span(true)
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();
}

// application layer
#[tracing::instrument(skip(repo, events), fields(order_id = %id))]
pub async fn confirm_order(
    id: OrderId,
    payment: PaymentConfirmation,
    repo: &dyn OrderRepository,
    events: &dyn EventPublisher,
) -> Result<OrderResult, ApplicationError> {
    tracing::info!("Confirming order");
    // ...
}
```

- Expose Prometheus metrics via `/metrics` using `metrics` + `metrics-exporter-prometheus`.
- Use OpenTelemetry SDK (`opentelemetry`, `tracing-opentelemetry`) for distributed tracing.
- Every service exposes `/health/live` and `/health/ready` endpoints.

---

## Build and Tooling

```toml
# Cargo.toml — required dev and CI tooling
[dev-dependencies]
mockall = "0.12"
testcontainers = "0.15"
tokio = { version = "1", features = ["macros", "rt-multi-thread", "test-util"] }
pretty_assertions = "1"

# .cargo/config.toml — enforce clippy in CI
[alias]
ci = "clippy --all-targets --all-features -- -D warnings"
```

Required CI checks (all must pass):
1. `cargo fmt --check` — formatting
2. `cargo clippy --all-targets -- -D warnings` — linting
3. `cargo test --all-features` — tests
4. `cargo audit` — dependency vulnerability scan
5. `cargo deny check` — license and dependency policy

Coverage target: **80% line coverage** measured by `cargo-llvm-cov`.

---

## Security

- Run `cargo audit` in CI. Block on any HIGH or CRITICAL advisories.
- Use `cargo deny` to enforce allowed licenses and block known-bad crate versions.
- No `unsafe` code without `// SAFETY:` justification and senior review.
- Validate all input at API boundaries using `validator` crate or manual checks.
- **Never log PII** — review `tracing::instrument` field lists carefully.
- Use `secrecy::Secret<String>` for sensitive config values to prevent accidental logging.

---

## Related Standards

- `../../CLAUDE.md` — Root engineering principles
- `../../api/CLAUDE.md` — API design (handlers, DTOs, versioning)
- `standards/overall/tech-stack.md` — Approved Rust libraries and frameworks
- `standards/detailed/microservices.md` — Microservice decomposition principles
