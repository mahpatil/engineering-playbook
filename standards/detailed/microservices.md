# Microservices Standards

Detailed standards for designing, building, and operating microservices in a cloud-native environment.

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Independent Deployability** | Teams ship features without coordinating releases, accelerating time to market |
| **Scalability** | Scale individual services under load without scaling the entire application |
| **Team Autonomy** | Small teams own full lifecycle of their service — design, build, deploy, operate |
| **Fault Isolation** | Failures are contained within service boundaries, preventing cascading outages |
| **Technology Flexibility** | Services choose the right tool for the job without forcing organization-wide changes |
| **Business Alignment** | Services map to business capabilities, reducing the cost of organizational change |
| **Resilience** | Independent services degrade gracefully; the system continues functioning under partial failure |

---

## Core Principles

### 1. Single Responsibility per Service
Each service owns one bounded context and does it well. A service should be cohesive — everything inside it changes for the same reason. If a service needs to be changed by multiple teams or for multiple unrelated reasons, it is too large.

**What this means:**
- Model services around business capabilities, not technical layers
- A service owns its domain data — no shared databases between services
- If a service has more than one distinct reason to change, split it
- Team ownership aligns to service ownership (Conway's Law)

**Example:** An `order-service` manages the lifecycle of orders. It does not also handle payments or inventory — those are separate services with their own bounded contexts.

---

### 2. Loose Coupling, High Cohesion
Services communicate through stable, versioned contracts. Internal implementation details are never exposed. Changes inside a service do not force changes in consumers.

**What this means:**
- Expose only what consumers need via explicit API contracts
- Avoid shared libraries that couple services at the code level
- Use asynchronous messaging for cross-service workflows to decouple timing
- Never share a database between services — the database is an implementation detail

**Example:** `payment-service` exposes a `POST /payments` endpoint. How it stores payment records internally is hidden. `order-service` calls the API, not the database.

---

### 3. Design for Failure
Every service will eventually fail. Design each service assuming its dependencies will be unavailable, slow, or returning errors. Resilience patterns are not optional — they are part of the service contract.

**What this means:**
- Implement circuit breakers for all downstream calls (e.g., Resilience4j, Hystrix)
- Apply timeouts to all external calls — never block indefinitely
- Use retries with exponential backoff and jitter for transient failures
- Degrade gracefully: return cached data or reduced functionality rather than a hard failure
- Bulkhead isolation: separate thread pools for critical vs non-critical dependencies

**Patterns:**
| Pattern | When to Apply |
|---------|--------------|
| Circuit Breaker | External service calls that may be unstable |
| Retry with backoff | Transient network and timeout errors |
| Timeout | All downstream HTTP and DB calls |
| Bulkhead | Critical paths that must not be starved by non-critical traffic |
| Fallback | User-facing flows where degraded response beats a failure |

---

### 4. Asynchronous Communication by Default
Prefer event-driven, message-based communication for cross-service workflows. Use synchronous calls only when the caller needs an immediate response to proceed.

**What this means:**
- Publish domain events when state changes (e.g., `OrderPlaced`, `PaymentProcessed`)
- Consumers subscribe to events independently — no tight temporal coupling
- Use a message broker (Kafka, RabbitMQ, Pub/Sub) for durable, ordered delivery
- Synchronous REST/gRPC is appropriate for query operations and real-time UX requirements
- Design events to be idempotent — consumers may receive duplicates

**Decision guide:**
- Synchronous: "I need the result now to continue" → REST or gRPC
- Asynchronous: "I need to notify others that something happened" → event/message

---

### 5. Stateless Services
Services do not retain in-memory state between requests. All state is stored in an external system (database, cache, message broker). This enables horizontal scaling and resilience.

**What this means:**
- No local session state — use distributed cache (Redis) or token-based auth (JWT)
- Containers are ephemeral — restart at any time without data loss
- Sticky sessions are an anti-pattern — any instance can serve any request
- Shared state lives in the data layer, not in service instances

---

### 6. API Contract as First-Class Artifact
Service interfaces are defined before implementation and treated as versioned contracts. Consumers depend on the contract, not the implementation.

**What this means:**
- Define OpenAPI or AsyncAPI specs before writing service code
- Contracts are stored in source control alongside the service
- Breaking changes require a new version — never modify a published contract in place
- Consumer-driven contract tests (Pact) prevent integration failures at deploy time
- Schema registries enforce compatibility for event schemas (e.g., Confluent Schema Registry)

---

### 7. Owned Data, Polyglot Persistence
Each service owns and manages its own data store. No other service accesses it directly. Services choose the data store type that best fits their workload.

**What this means:**
- No shared schemas or shared database connections across service boundaries
- Use the right database for the job: relational, document, time-series, graph, key-value
- Cross-service data access goes through the service API, not a shared DB query
- Eventual consistency is the norm for cross-service data — design for it explicitly

---

### 8. Observability Built In
Every service emits structured logs, metrics, and distributed traces from day one. Observability is a deployment requirement, not a post-launch activity.

**What this means:**
- Structured JSON logs with correlation IDs propagated across service calls
- Metrics exposed in Prometheus format: request rate, error rate, latency (RED method)
- Distributed tracing with OpenTelemetry — trace IDs flow across all service boundaries
- Health endpoints: `GET /health/live` and `GET /health/ready` on every service
- Dashboards and alerts defined as code alongside the service

**Minimum instrumentation per service:**
| Signal | Standard |
|--------|----------|
| Logs | Structured JSON, correlation ID, severity level |
| Metrics | Request rate, error rate, p95/p99 latency, queue depth |
| Traces | OpenTelemetry spans for all inbound and outbound calls |
| Health | `/health/live` (is the process alive) and `/health/ready` (can it serve traffic) |

---

### 9. Automated Deployment Pipeline
Every service has its own independent CI/CD pipeline. Services are deployed independently — not as part of a coordinated release train.

**What this means:**
- Each service has its own pipeline: build → test → security scan → deploy
- Contract tests run before integration tests
- Blue/green or canary deployments to minimize blast radius
- Rollback is automated — a failed health check triggers automatic reversion
- Feature flags decouple deployment from release

---

### 10. Security at Every Boundary
All inter-service communication is authenticated and authorized. Services never trust an incoming request implicitly.

**What this means:**
- mTLS for all service-to-service communication within the cluster
- JWT or OAuth 2.0 tokens for API access — validate on every request
- Network policies restrict which services can communicate (default deny)
- Secrets injected at runtime via a vault (HashiCorp Vault, AWS Secrets Manager) — never in environment variables or config files
- Principle of least privilege: each service has only the permissions it needs

---

### 11. Service Sizing and Team Alignment
Services should be sized such that a small team (2–8 engineers) can fully own the service: design, build, test, deploy, and operate it. If a service requires more, consider splitting it.

**What this means:**
- A service that takes more than two weeks for one person to understand is too large
- Services should be deployable in under 10 minutes from commit to production
- Avoid nanoservices: if two services always deploy together and never fail independently, merge them
- Prefer extracting services when a capability needs to scale independently or be reused

---

## Operational Standards

| Practice | Requirement |
|----------|-------------|
| Health checks | All services expose `/health/live` and `/health/ready` |
| Graceful shutdown | Services drain in-flight requests before terminating |
| Resource limits | All containers have CPU and memory limits defined |
| Startup probes | Prevent traffic before service is ready |
| Chaos testing | Failure scenarios tested regularly (e.g., Chaos Monkey, Gremlin) |
| Runbooks | Each service has an operational runbook linked from its README |

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Shared database | Tight coupling, prevents independent evolution | Each service owns its data |
| Chatty synchronous chains | Latency amplification, cascading failures | Async events for cross-service workflows |
| Distributed monolith | Services deploy together, fail together | True independent deployability |
| Shared mutable libraries | Changes propagate unexpectedly across services | Stable versioned APIs, not shared code |
| Synchronous sagas | Blocking distributed transactions | Choreography or orchestration with compensation |
| Fat services | Too many responsibilities, too many owners | Split by bounded context |
