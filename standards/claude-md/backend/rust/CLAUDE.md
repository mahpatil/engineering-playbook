# Rust Backend Standards

Extends ../../CLAUDE.md.

## Toolchain
- Stable 1.90+, edition 2024, pinned in `rust-toolchain.toml` (`channel = "1.90"`, `components = ["rustfmt","clippy"]`). Nightly only for benchmarks and the CI-only branch-coverage job below, never for release builds.
- Do not use `#![deny(warnings)]` (breaks on new compiler lints); CI passes `-D warnings` instead.
- Approved stack: Tokio, Axum 0.8 + `tower`/`tower-http`, SQLx 0.8 (Postgres), `thiserror` 2 (libraries/domain), `anyhow` (`main` only), `serde`, `config`, `tracing` + `tracing-subscriber`, `tracing-opentelemetry`, `reqwest`, `secrecy`, `validator`, `mockall`, `testcontainers` + `testcontainers-modules`.
- Newtypes for IDs (`struct OrderId(Uuid)`). Result enums for domain outcomes. No `Box<dyn Error>` in library code.
- Async traits: native `async fn` in traits for static dispatch; `#[async_trait]` only when a port is used as `&dyn`/`Arc<dyn>`.
- Blocking or CPU-bound work in async code goes through `tokio::task::spawn_blocking`. Tokio is the only runtime.
- `unsafe` requires a `// SAFETY:` comment (clippy `undocumented_unsafe_blocks`) and senior review.

## Layout
```
src/{domain,application,infrastructure,api}/  config.rs  error.rs  main.rs
tests/{integration,contract}/   migrations/   .sqlx/
```
`application/ports.rs` holds repository traits; `api/` holds `handlers/` and `dto/`. Unit tests live in `#[cfg(test)]` modules. Boundaries via module visibility (`pub(crate)`, `pub(super)`); for a workspace, one crate per layer so `cargo deny`/Cargo dependencies enforce direction. `.sqlx/` is committed (`cargo sqlx prepare`) and CI sets `SQLX_OFFLINE=true`.

## Axum 0.8
- Path params use braces: `/orders/{id}/confirm` (the `/:id` and `/*rest` forms are 0.7 and panic at startup in 0.8; wildcards are `/{*rest}`).
- Handler traits no longer need `#[async_trait]`; custom extractors implement `FromRequestParts` with native async.
- `Option<T>` as an extractor requires `OptionalFromRequestParts`; do not assume it swallows all rejections.
- Serve with `axum::serve(TcpListener, app).with_graceful_shutdown(...)`.
- Middleware via `tower-http`: `TraceLayer`, `SetRequestIdLayer` + `PropagateRequestIdLayer` (header `x-request-id`), `CompressionLayer`, `TimeoutLayer`, and `CorsLayer` with an explicit origin allowlist (never `permissive()` outside local dev).
- Routes `/health/live`, `/health/ready` (checks DB pool), `/metrics` (`metrics-exporter-prometheus`).
```rust
Router::new()
    .route("/orders", post(create_order))
    .route("/orders/{id}", get(get_order))
```

## Errors
`ApplicationError` (`thiserror`) implements `IntoResponse`, producing the RFC 9457 body from the root. Log it in the `IntoResponse` impl or a `TraceLayer` hook, not in domain code. Non-transparent `#[from]` conversions must not leak into the body.

| Variant | Status |
|---|---|
| `NotFound` | 404 |
| `Validation` | 422 |
| `BusinessRule` (state conflict) | 409 |
| `ExternalService` (`reqwest::Error`) | 502 (generic detail) |
| `Database` (`sqlx::Error`) | 500 (generic detail); unique-violation maps to 409 |

No `unwrap()`/`expect()` outside tests and startup (clippy lints below).

## Configuration
`config` crate into typed `serde` structs; environment variables in production (`APP__DATABASE__URL`), files for local dev only. Secrets as `secrecy::SecretString` (not `Secret<String>`, deprecated). Load and validate in `main` before binding the listener.

## Persistence
SQLx checked macros (`query_as!`); repositories map rows to domain types. Migrations via `sqlx-cli`, applied with `sqlx::migrate!`. One `PgPool` in `AppState`.

## Testing
- `mockall` (`#[automock]`) on port traits. Integration tests use `testcontainers-modules` (`postgres::Postgres`) with the `AsyncRunner` API (`Postgres::default().start().await?`), running real migrations.
- `pact_consumer` for consumer contracts; provider verification on every CI build.

## Observability and resilience
- `tracing_subscriber::fmt().json().with_current_span(true)` with `EnvFilter`; `#[tracing::instrument(skip(repo), fields(order_id = %id))]` on use cases, always skipping secrets and PII. Root log fields go on the request span via middleware; OTLP via `tracing-opentelemetry`.
- `reqwest::Client::builder().timeout(..)` always. Retry idempotent calls only, on connect/timeout errors or 5xx, with `tower::retry` or `backon` (`backoff` is unmaintained). Circuit breaker: `failsafe` (tower has none built in).

## Enforcement
```toml
# Cargo.toml
[lints.rust]
unsafe_op_in_unsafe_fn = "deny"
[lints.clippy]
all = { level = "deny", priority = -1 }
unwrap_used = "deny"
expect_used = "deny"
undocumented_unsafe_blocks = "deny"
cognitive_complexity = "deny"
# clippy.toml
cognitive-complexity-threshold = 15
allow-unwrap-in-tests = true
allow-expect-in-tests = true
```
`deny.toml`: `[advisories] yanked = "deny"`, explicit `[licenses] allow`, `[bans] multiple-versions = "warn"`, `wildcards = "deny"`.

CI, all required:
1. `cargo fmt --check`
2. `cargo clippy --workspace --all-targets --all-features -- -D warnings`
3. `cargo test --workspace --all-features`
4. `cargo audit` and `cargo deny check`
5. `cargo llvm-cov --workspace --fail-under-regions 80`

Coverage limitation: `cargo-llvm-cov` has no branch-coverage gate on stable. `--branch` needs nightly and `--fail-under-*` has no branch option. Stable CI therefore gates 80% region coverage (the closest enforceable proxy, which counts conditional branches within expressions). A CI-only nightly job runs `cargo +nightly llvm-cov --branch --summary-only` and fails if the reported branch percentage is under 80 (parse the summary).
