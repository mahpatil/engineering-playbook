# CLAUDE.md

## Project

- Name: {{APP_NAME}}
- Type: {{APP_TYPE e.g. microservice, frontend, fullstack}}
- Domain: {{BUSINESS_DOMAIN e.g. payments, catalog, auth}}

## Tech Stack

- **Backend:** Java 25+ / Spring Boot 4.0+ / Gradle
- **Frontend:** React 19+ / TypeScript 5.x (strict) / Vite, design system (select most appropriate: carbon, fluent2, apple human, materialm3, polaris)
- **Database:** PostgreSQL (managed cloud service), Redis for caching
- **Infra:** Docker / Kubernetes / Terraform / Cloud (AWS/GCP/Azure)
- **Messaging:** Kafka or managed cloud eventing (e.g., GCP Pub/Sub, Azure Event Hubs) (Avro/Protobuf schemas)
- **CI/CD:** GitHub Actions

## Deployment

- **IaC**: use Terraform to setup cloud resources (provider-agnostic)
- **Local**: for local deployment generate k8s for kind & minikube

## Architecture

- Open source and open standards
- Ensure all software is portable across cloud providers. Abstract cloud-specific implementations
- Hexagonal architecture: Domain (no framework deps) → Application → Infrastructure (adapters)
- Domain-Driven Design with bounded contexts, aggregates, value objects, domain events
- Event-driven integration between services (outbox pattern, saga for workflows)
- API-First design with OpenAPI specs
- Cost efficient - Implement FinOps from day one right-size, monitor spending, auto-scaling
- CQRS where read/write complexity (only if required)

## Code Standards

- Constructor injection only (no @Autowired)
- Use Java records, sealed classes, pattern matching, virtual threads
- Functional React components with hooks, no class components
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Trunk-based development: feature branches < 2 days, main always deployable

## Testing

- Unit tests > 80% coverage (JUnit 5 / Jest)
- Integration tests with Testcontainers
- Contract tests with Pact
- E2E tests for critical paths
- Performance tests with Grafana K6

## Security

- Zero Trust: mTLS between services, OAuth + JWT for auth
- No secrets in code — use secret manager
- OWASP dependency checks in CI
- Least privilege access, validate at system boundaries

## Resilience

- Circuit breaker, retry, bulkhead, rate limiter (Resilience4j)
- Health checks: liveness + readiness probes
- Feature flags for safe rollouts, canary deployments

## Observability

- OpenTelemetry for traces, metrics, structured logging
- SLOs defined for latency, availability, error rate
- Dashboards in Grafana, alerts for SLO breaches

## Project Structure

```text
.github/workflows/    # CI/CD pipelines
services/             # Backend microservices
  {{SERVICE_NAME}}/
    src/main/java/
      domain/         # Entities, value objects, domain events
      application/    # Use cases, ports (interfaces)
      infrastructure/ # Adapters, config, persistence
ui/                   # React frontend
infra/                # Terraform + K8s manifests
docs/                 # ADRs, API docs, runbooks
```

## App-Specific Context

{{DESCRIBE KEY BUSINESS RULES, DOMAIN CONCEPTS, AND INTEGRATION POINTS}}
