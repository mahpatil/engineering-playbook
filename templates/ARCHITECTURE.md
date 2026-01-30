Title: Architecture Overview

1. Context
<Brief description of the system purpose, users, and core capabilities>

2. Modules
- api-java: Spring Boot REST API; request validation, auth, routing.
- service-java: Domain services; business rules, orchestration.
- data-java: Persistence adapters; JPA repositories, migrations.
- worker-python: Async job processor; scheduled tasks, queues.
- lib-python: Shared utilities; clients, DTOs, validation.
- infra: Config, Dockerfiles, deployment manifests.

3. Data flow
- Request enters api-java → validated → delegated to service-java.
- service-java loads/updates domain entities via data-java.
- Events emitted to message bus; worker-python consumes and performs asynchronous processing.
- lib-python provides shared clients for external integrations.

4. Patterns
- Ports & Adapters (Hexagonal): Domain isolates infrastructure.
- CQRS (lightweight): Separate read models where beneficial.
- Event-driven: Async processing for non-critical paths.
- Configuration-as-code: Externalized via env; 12-factor principles.

5. Dependencies
- Java: Spring Boot, JPA/Hibernate, Jackson, Micrometer.
- Python: FastAPI or none (worker only), pydantic, aiohttp, pytest.
- Infra: Postgres, Redis, Kafka/RabbitMQ (as applicable).

6. Service boundaries
- api-java exposes HTTP endpoints; service-java has no network endpoints.
- worker-python subscribes to queues; no direct HTTP exposure.
- Cross-service communication via messages; avoid synchronous coupling.

7. Interfaces
- Java interfaces: `PriceService`, `OrderRepository`, `PaymentGateway`.
- Python protocols: `MessageBroker`, `StorageClient`, `MetricsSink`.

8. Observability
- Metrics: Request latency, error rates, queue lag, job durations.
- Tracing: Distributed traces across Java and Python services.
- Logging: Structured JSON; correlation IDs propagate across boundaries.

9. Migration notes
- Legacy module migration paths, compatibility shims, phased rollout via flags.