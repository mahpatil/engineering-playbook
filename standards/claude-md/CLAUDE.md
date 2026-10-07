# Engineering Standards — Root

Cross-cutting rules for every service and library. Language, API, frontend and infra files extend this one and must not restate it. Rules a linter or CI check enforces live in config, not here.

## Principles
- Clarity over cleverness. Small, safe, reviewable changes. Quality and security are built in from the first line.
- Names reveal intent; booleans read as assertions (`isActive`, `canRetry`). No magic numbers: use named constants.
- Complexity limits (cyclomatic ≤ 10, cognitive ≤ 15, method ≤ 40 lines) are enforced by lint config, not by review.
- Depend on abstractions; inject dependencies through constructors. No service locators or static factories.

## Structure
Layers: `domain/` (no framework imports) ← `application/` (use cases, ports) ← `infrastructure/` (adapters) and `api/` (controllers, DTOs). Domain and application never import `infrastructure` or `api`; enforce with ArchUnit, NDepend, `import-linter` or `cargo deny`/module visibility. Tests: `unit/` (no I/O), `integration/` (real dependencies), `contract/` (Pact), `e2e/` (critical journeys only). Docs: `docs/adr/`, `docs/runbooks/`.

## Testing
- Unit tests mock at ports only. Persistence tests use real databases (Testcontainers); never mock the DB or substitute SQLite for Postgres.
- Test names state behaviour: `should_return_404_when_user_not_found`. Tests are independent, order-free and never sleep; poll instead.
- Coverage floor: 80% **branch** coverage on business logic, enforced in CI config. A flaky test is a bug: fix or quarantine it the same day.
- E2E covers the top 5-10 journeys. Performance: P95 latency and throughput under k6.

## Security
- No secrets in code or history; use a secrets manager. Validate and sanitize all input at every boundary, including queues and internal callers.
- Least privilege for service accounts, IAM roles and DB users. Zero trust: authenticate and authorize every call; mTLS between services.
- Parameterized queries only. Standard OAuth 2.0/OIDC; never custom auth. TLS 1.2+ in transit, AES-256 at rest. Never log PII, passwords or tokens.
- Pin dependencies; scan every CI build and block on critical CVEs; drop unmaintained libraries (no commits for 2+ years).

## Errors
- Fail fast. Never swallow an exception: log, rethrow, or comment why silence is correct. Log at the boundary, not in domain code.
- Never expose stack traces or SQL errors in responses.
- Error bodies are [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457) with `type`, `title`, `status`, `detail`, `instance`, `correlationId` and, for validation, `errors[{field,message}]`.
- Status mapping: validation failure 422; state conflict or business-rule violation 409; idempotency key reused with a different payload 422. Full table in `api/CLAUDE.md`.

## Observability
- JSON structured logs with `timestamp`, `level`, `service`, `traceId`, `spanId`, `correlationId`, `message`. Log events, not state.
- OpenTelemetry SDK only (no vendor SDKs). Propagate `traceparent` over HTTP and messaging; trace databases, caches, HTTP clients and brokers.
- Default SLOs: availability 99.9%, P95 < 500 ms, P99 < 2 s, error rate < 0.1%.
- Every service exposes `/health/live` and `/health/ready` (map framework paths such as Spring Actuator to these).

## Documentation
- An ADR in `docs/adr/` (MADR) precedes any significant decision and records context, options, decision and consequences.
- Comments explain why, not what. No commented-out code. TODOs carry a ticket: `TODO(PROJ-123)`.
- Every production service has a runbook: deploy and rollback, health checks, known failure modes, escalation.

## Git
- Conventional Commits (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `security`), DCO-signed (`-s`).
- Trunk-based: `main` is always deployable. Branches `feature/<ticket>-slug` live under 2 days; use feature flags for longer work. `main` needs green CI and one approval.
- PRs state what changed, why and how it was tested; aim for under 400 changed lines. Never merge with failing tests, lint errors or open security findings.

## Performance
Profile before optimizing. Avoid N+1 queries and verify plans with `EXPLAIN ANALYZE` on realistic data. Plan cache invalidation with every cache. Size pools from load tests. All external calls are async.

## Data governance
Classify data as Public, Internal, Confidential or Restricted. Restricted (PII, PCI, PHI) needs explicit approval, immutable audit logs of access and mutation, implemented (not just documented) retention, and GDPR/CCPA deletion and export from the start.

## Related
`ai/` (agent usage and LLM features), `api/`, `frontend/`, `infra/`, `backend/{java,dotnet,python,rust}/` CLAUDE.md files. `standards/overall/principles.md` and `tech-stack.md` for architecture and approved technology.
