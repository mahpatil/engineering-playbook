# Engineering Standards — Root

This file defines cross-cutting engineering principles that apply to every service, library, and component in this codebase. More specific guidance lives in subdirectory CLAUDE.md files — this file sets the floor.

---

## Core Philosophy

**Clarity over cleverness.** Code is read 10x more than it is written. Optimize for the next engineer, not for terseness or personal style.

**Small, safe changes.** Prefer many small commits over large PRs. A change that is easy to review, test, and roll back is inherently lower risk.

**Quality and security are not optional.** They are not post-delivery tasks. They are built in from the first line of code.

---

## Code Quality

### Naming

- Names must be descriptive and intention-revealing. `getUserById` not `getUser`, `processPaymentRefund` not `process`.
- Avoid abbreviations unless universally understood in the domain (`id`, `url`, `api`, `dto` are fine; `mgr`, `hlpr`, `proc` are not).
- Boolean variables and methods must read as assertions: `isActive`, `hasPermission`, `canRetry`.
- Constants are `SCREAMING_SNAKE_CASE`. Classes are `PascalCase`. Methods and variables are `camelCase` (Java/.NET) or `snake_case` (Python/Go).
- File names match the primary class or module they contain.

### Complexity

- Functions do **one thing**. If you need "and" to describe what a function does, split it.
- Cyclomatic complexity must not exceed **10** per method. Prefer early returns over deeply nested conditionals.
- Maximum method length: **40 lines** (excluding blank lines and comments). If a method is longer, it is doing too much.
- No magic numbers or strings. Extract to named constants with a comment explaining the value's origin.

```java
// BAD
if (retries > 3) { ... }

// GOOD
private static final int MAX_RETRY_ATTEMPTS = 3; // aligned with SLA for transient failures
if (retries > MAX_RETRY_ATTEMPTS) { ... }
```

### SOLID Principles

- **Single Responsibility**: One reason to change per class.
- **Open/Closed**: Extend via composition and interfaces, not by modifying existing classes.
- **Liskov Substitution**: Subtypes must honour the contract of their supertypes.
- **Interface Segregation**: Prefer narrow, focused interfaces over broad ones.
- **Dependency Inversion**: Depend on abstractions. Inject dependencies; do not instantiate them.

**Do not use service locators or static factories for dependency resolution.** Constructor injection is the only acceptable DI pattern.

---

## Project Structure

All projects follow a layered structure that keeps domain logic independent of frameworks:

```
src/
  domain/           # Entities, value objects, domain events — ZERO framework dependencies
  application/      # Use cases, ports (interfaces), application services
  infrastructure/   # Adapters: persistence, messaging, HTTP clients, config
  api/              # Controllers, request/response DTOs, OpenAPI annotations
tests/
  unit/             # Fast, no I/O, mock at ports
  integration/      # Real dependencies (Testcontainers or equivalent)
  contract/         # Consumer-driven contract tests
  e2e/              # Critical user journeys only
docs/
  adr/              # Architecture Decision Records
  runbooks/         # Operational procedures
```

Domain code must never import from `infrastructure` or `api` packages. Application code may not import from `infrastructure`. Enforce this with ArchUnit or NDepend.

---

## Testing

### The Testing Pyramid

| Layer | Coverage Target | Tooling |
|---|---|---|
| Unit | >80% line coverage | JUnit 5 / xUnit / Jest |
| Integration | Key data flows | Testcontainers / WebApplicationFactory |
| Contract | All provider/consumer pairs | Pact |
| E2E | Top 5-10 critical journeys | Playwright / Selenium |
| Performance | P95 latency + throughput | Grafana K6 |

### Rules

- Tests are **first-class code**. Apply the same quality standards as production code.
- Test names document intent: `should_return_404_when_user_not_found`, not `testGetUser2`.
- One assertion per test where possible. Multiple assertions require a meaningful test name that covers all cases.
- Never use `Thread.sleep` in tests. Use `Awaitility` or equivalent polling utilities.
- No shared mutable state between tests. Each test is fully independent and can run in any order.
- Tests must pass **100% of the time** in CI. Flaky tests are treated as bugs and fixed immediately.
- Use real dependencies (Testcontainers) for persistence tests. Do not mock databases.

### Coverage

80% is the minimum, not the target. Focus coverage on business logic, not getters/setters or framework glue. Measure **branch coverage**, not just line coverage.

---

## Security

### Non-Negotiables

- **No secrets in code.** No API keys, passwords, connection strings, or certificates in source files or commit history. Use a secrets manager (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, HashiCorp Vault).
- **Validate at every boundary.** Validate and sanitize all input at API boundaries. Never trust data from external systems, message queues, or even internal callers without validation.
- **Least privilege.** Service accounts, IAM roles, and database users get only the permissions they need — nothing more.
- **Zero Trust.** No implicit trust between services. Authenticate and authorize every call. Use mTLS for service-to-service communication.

### OWASP Top 10 — Always Check

- **Injection**: Use parameterized queries. Never concatenate user input into SQL, shell commands, or LDAP queries.
- **Broken Authentication**: Use industry-standard OAuth 2.0 / OIDC. Never roll your own auth.
- **Sensitive Data Exposure**: Encrypt data at rest (AES-256) and in transit (TLS 1.2+). Never log PII, passwords, or tokens.
- **Security Misconfiguration**: Disable unused features and endpoints. Remove default credentials. Harden default configs.
- **Vulnerable Dependencies**: Run OWASP Dependency Check or Dependabot in CI. Block builds on critical CVEs.

### Dependency Management

- Pin dependency versions. Review and update regularly.
- Run automated vulnerability scans on every CI build.
- No abandoned libraries (last commit > 2 years, no maintainers).

---

## Error Handling

### Principles

- **Fail fast and explicitly.** Throw meaningful exceptions early rather than propagating invalid state.
- **Never swallow exceptions.** A caught exception must be logged, re-thrown, or explicitly handled with a comment explaining why silence is correct.
- **Distinguish recoverable from unrecoverable errors.** Domain validation errors are recoverable; infrastructure failures may not be.
- **Expose errors appropriately.** Internal error details (stack traces, SQL errors) must never reach API responses in production.

```java
// BAD — swallowed exception
try {
    process();
} catch (Exception e) {
    // ignore
}

// BAD — implementation details leaked
return ResponseEntity.status(500).body(e.getMessage());

// GOOD — structured error with no internal detail
return ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR,
    "An unexpected error occurred. Reference: " + correlationId);
```

### Error Response Shape

All errors use [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457):

```json
{
  "type": "https://errors.example.com/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "The request body failed validation.",
  "instance": "/orders/123",
  "correlationId": "abc-123-xyz",
  "errors": [
    { "field": "email", "message": "must be a valid email address" }
  ]
}
```

---

## Observability

Every service **must** be observable from day one. Observability is not a feature you add later.

### Structured Logging

- Use JSON structured logging. No unstructured `System.out.println` or `console.log` in production code.
- Every log line includes: `timestamp`, `level`, `service`, `traceId`, `spanId`, `correlationId`, `message`.
- Log **events** (what happened), not **states** (what is). Log at the boundary, not inside domain logic.

```json
{
  "timestamp": "2025-03-31T12:00:00Z",
  "level": "INFO",
  "service": "order-service",
  "traceId": "abc123",
  "correlationId": "req-xyz",
  "event": "order.created",
  "orderId": "ord-456",
  "customerId": "cust-789",
  "amount": 149.99
}
```

**Never log PII** (names, emails, card numbers, SSNs) outside of audit logs that have appropriate access controls.

### Metrics

Define and instrument SLOs from day one:

| SLO | Default Target |
|---|---|
| Availability | 99.9% (three nines) |
| P95 Latency | < 500ms |
| P99 Latency | < 2s |
| Error Rate | < 0.1% |

Every service exposes a `/health/live` and `/health/ready` endpoint.

### Distributed Tracing

- Use OpenTelemetry SDK. Do not use vendor-specific tracing SDKs.
- Propagate `traceparent` header across all HTTP and messaging calls.
- Trace all external calls: databases, caches, HTTP clients, message brokers.

---

## Documentation

### Architecture Decision Records (ADRs)

Every significant technical decision gets an ADR in `docs/adr/`. Use the [MADR template](https://adr.github.io/madr/). An ADR answers:
- What is the context and problem?
- What were the options considered?
- What was decided and why?
- What are the consequences?

An ADR is written **before** the implementation, not after.

### Code Comments

- Comment **why**, not **what**. The code says what; the comment says why it was necessary.
- Complex algorithms and non-obvious business rules must have explanatory comments.
- Do not leave commented-out code in the codebase. Delete it. Git history preserves it.
- TODO comments must include a ticket reference: `// TODO(PROJ-123): refactor after migration`.

### Runbooks

Every production service has a runbook in `docs/runbooks/` covering:
- How to deploy and roll back
- How to check service health
- Known failure modes and remediation steps
- Escalation path and on-call contacts

---

## Git & Version Control

### Conventional Commits

All commits follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer(s)]
```

| Type | Use for |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `chore` | Tooling, dependencies, build config |
| `perf` | Performance improvement |
| `security` | Security fix |

### Branching

- **Trunk-based development.** `main` is always deployable.
- Feature branches: `feat/<ticket-id>-short-description`. Live for < 2 days.
- No long-lived branches. If a feature takes weeks, use feature flags.
- Branch protection: `main` requires passing CI + 1 approver review.

### Pull Requests

- Every PR has a clear description: what changed, why, and how to test.
- PR size: aim for < 400 lines changed. Larger PRs require justification.
- No PR is merged with failing tests, lint errors, or unresolved security findings.
- Self-review before requesting peer review.

---

## Performance

- Benchmark before optimizing. Use profiling data, not intuition.
- Avoid N+1 query patterns. Use `EXPLAIN ANALYZE` to verify query plans on realistic data volumes.
- Cache at the right layer (application, CDN, DB query cache) — but always plan for cache invalidation.
- Set connection pool sizes based on load testing, not defaults.
- Async I/O for all external calls. Blocking the main thread for network I/O is never acceptable.

---

## Compliance & Data Governance

- Classify data: **Public**, **Internal**, **Confidential**, **Restricted**.
- Restricted data (PII, PCI, PHI) requires explicit approval for storage and processing.
- Data retention policies must be implemented, not just documented.
- Audit logs for all data access and mutations on Restricted data. Audit logs are immutable.
- GDPR/CCPA: implement data deletion and export capabilities for user data from the start.

---

## Related Standards

- `infra/CLAUDE.md` — Infrastructure and IaC standards
- `backend/java/CLAUDE.md` — Java/Spring Boot specifics
- `backend/dotnet/CLAUDE.md` — .NET/ASP.NET Core specifics
- `api/CLAUDE.md` — API design and contract standards
- `frontend/CLAUDE.md` — Frontend component and UX standards
- `standards/overall/principles.md` — 13 cloud-native engineering principles
- `standards/overall/tech-stack.md` — Approved technology choices
