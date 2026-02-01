# Domain-Driven Cloud Native Microservice

## Overview
<!--This document outlines the architecture and implementation guidelines for building a production-ready, domain-driven, cloud native microservice using modern Java Spring back-end and react front-end technologies.-->
A full-stack e-commerce demonstration featuring microservices (Java 21/Spring) and a React frontend with Google OAuth and local authentication. Supports deployment on both local Kind clusters and GCP Cloud Run with minimal infrastructure overhead.

## Principles

1. **Composable Architecture & Domain-Driven Design** - Focus on separation of concerns, bounded contexts, and ubiquitous language for maintainability
2. **Microservices, API-First, Cloud-Native (MACH) and containers** - Design independent services with clear contracts, RESTful APIs, cloud native, conatiner-first and eventual consistency for system flexibility
3. **Portability** - Ensure all software is portable across providers and abstract cloud-specific implementations to enable seamless multi-cloud deployments without vendor lock-in
4. **Observability** - Implement distributed tracing, structured logging, and metrics, alerts for complete system visibility and rapid issue resolution
5. **Zero Trust Security** - Assume the environment is compromised; authenticate, authorize, and encrypt all flows across all layers; mTLS for service-to-service communication
6. **Performance & Optimization** - Optimize through intelligent caching, compression, and efficient algorithms for minimal latency
7. **High Availability** - Design for redundancy, failover mechanisms, and graceful degradation under failure conditions
8. **Reliability** - Ensure data consistency, fault tolerance, backup and restore/recovery mechanisms, cross-region replication to meet SLO/SLA requirements, chaos engineering & testing.
9. **Cost Optimization** - Right-size resources, monitor spending, use auto-scaling and spot instances to minimize cloud waste
10. **Automation First** - Integrate CI/CD, automated testing, and security scanning into every stage from requirements through deployment
11. **Infrastructure as Code** - Treat all infrastructure, configuration, and deployments as version-controlled, repeatable code artifacts

## Technology Stack

### Stack & Technology
- **API Gateway**: Native API Gateway for rate limiting at the edge, request routing, or API composition patterns
- **Backend**: Latest Java LTS (25+), Spring Boot 4.0+, Gradle (multi-module monorepo)
- **Frontend**: React with TypeScript, Vite
- **Spring Cloud**: Microservices patterns and distributed system support
- **Containers**: Docker for all services
- **Orchestration**: Kubernetes (Kind locally, Cloud Run on GCP)
- **Infrastructure**: Terraform for IaC to setup core GCP resources
- **Database**: CloudSQL (GCP), local SQL/H2 for development
- **Caching**: Redis, cloud native
- **Secrets**: GCP Secrets manager for runtime, GitHub secrets for build
- **Events/Integration**: GCP Pub/Sub, Kafka
- **Config**: YAML for all Kubernetes and application configs
- **OpenTelemetry**: Unified observability (traces, metrics, logs)
- **React 19+**: Latest react library for web and native use interfaces.


### Architecture Patterns
1. **Hexagonal Architecture**: Ports and adapters for clean separation
2. **Event-Driven Architecture**: Asynchronous communication where appropriate, with dead-letter queue handling, schema registry (Avros schemas)
3. **Team Autonomy** - Organize teams and services around business domains; enable independent deployment and ownership (Conway's Law)
4. **Resilience Patterns** - Explicitly implement circuit breakers, retries, timeouts, and bulkheads for fault tolerance beyond basic reliability
5. **Backwards Compatibility** - Maintain API/contract stability across versions; support multiple versions during transitions to enable independent service evolution
6. **Immutability** - Use immutable containers, infrastructure, and deployments to ensure consistency and simplify debugging/rollback
7. **Graceful Degradation** - Services should fail safely with reduced functionality rather than complete outage; prioritize critical paths
8. **Statelessness** - Services should be stateless to enable horizontal scaling and cloud portability; externalize all state to persistent stores

### Deployment
- Follow **trunk based development**, main/master is protected and is what is deployed
- Generate manifests for **local kubernetes** (viz kind) deployment
- Use **terraform** for setting up common resources on **GCP** (but not for application deployment and config)
- **GitHub actions** for deployment of applications and configuration to GCP 
- **Modularize build and deployment workflows**, create separate files and orchestrate as required (avoid large monolithic build pipelines)
- **Environments** Assume two environments Non production and production, both deployed across separate GCP Projects
- **Promotion to prod** can only happen after successful non production deployments
- Generate **versioned immutable artefact** after every build
- Automate **release notes** creation
- **Testing** is fully automated and includes security scanning, unit, integration, contract and integration testing; follow pyramid test strategy
 
### Tools

| Tools | Capabilities | Details |
|---------|----------|----------|
| GitHub  | Source Control, Secrets   | All code to be maintained in GitHub   |
| GitHub Actions  | Build and Deploy pipelines   | All build and deployment via GitHub Actions   |
| Code quality and security  | Sonar Scanner  | Static Code Aanalysis   |
| Build scripting| Gradle, npm | Gradle for all java build scripting, npm for front-end node |
| Secret Management  | GitHub Secrets & GCP   | Secrets for build and deploy in GitHub and GCP for runtime secrets   |
| Infrastructure as Code | Terraform | All infrastructure provisioning to be done via Terraform  |
| IDE | VS Code   | Engineers to use VSCode as IDE  |
| Artifact management | GCP Artifact Registry   | All generated artifadcts  |
| Unit testing | Junit (Java), Jest(JS)   | Junit for java tests, Jest for javascript  |
| Contract testing | PACT   | contract-based testing for Consumer-Driven tests |
| Integration testing | Cucumber, Testcontainers  | BDD Style tests for integration tests  and test containers to manage services|
| Performance testing | Grafana K6    |  Use K6 for load and performance testing of critical flows  |

2. Comprehensive Observability
OpenTelemetry integration for unified traces, metrics, logs
Structured logging with key-value pairs (line 201-206)
Custom business metrics instrumentation
Prometheus alerting rules included

3. Resilience Patterns
Resilience4j with circuit breaker, retry, bulkhead, and time limiter
Fallback methods demonstrated
Graceful shutdown configured

4. Testing Strategy

Multi-layer testing: unit, integration, contract, performance
Testcontainers for realistic integration tests
Security testing included
5. Security Considerations
OAuth2/JWT resource server configuration
OWASP dependency check in CI/CD
Non-root Docker user
CSP headers configured
Missing Service Mesh / mTLS
ServiceMesh/mTLS for service-to-service security

6. Kubernetes-Native

Health probes (liveness/readiness) configured
HPA with CPU/memory scaling
Resource requests/limits defined

No feature flags (LaunchDarkly, Unleash, ConfigMaps-based)
No distributed tracing correlation across async boundaries
No cost optimization (spot instances, resource right-sizing)
No multi-tenancy patterns
11. API Documentation

No OpenAPI/Swagger specification
Contract tests use Spring REST Docs but no API-first design discussion

2. Cache Invalidation Across Instances

Redis caching shown but no pub/sub for cache invalidation
No cache-aside vs. write-through strategy discussion

## Project Structure
### Overall
```
.github                  # GitHub build & deployment workflows 

services/               # Microservices
  ├── auth-service/     # Google OAuth + local auth (JWT tokens)
  ├── catalog-service/  # Product catalog (Bath & Body Works dataset)
  ├── cart-service/     # Shopping cart management
  └── libs/jwt-common/  # Shared JWT utilities for downstream services
ui
  ├── commons/          # Common libraries and micro-frontends
  ├── storefront-ui/    # React + TypeScript frontend (Vite)
  └── mobile-ui         # ReactNative

infra/                  # Infrastructure as Code
  ├── gcp/              # GCP deployment scripts
  └── kind/             # Kind cluster setup and K8s manifests
```

### Java services
```
src/main/java/
├── domain/             # Core business logic (no framework dependencies)
│   ├── model/          # Entities, Value Objects, Aggregates
│   ├── repository/     # Repository interfaces (ports)
│   ├── service/        # Domain services
│   └── event/          # Domain events
├── application/         # Application services and use cases
│   ├── command/        # Command handlers
│   ├── query/          # Query handlers
│   └── dto/            # Data transfer objects
├── infrastructure/      # Technical implementations (adapters)
│   ├── persistence/    # JPA/database implementations
│   ├── messaging/      # Event publishing/consuming
│   ├── cache/          # Caching implementations
│   └── external/       # External service clients
└── api/                # REST/GraphQL controllers
    ├── rest/
    └── graphql/
```

## Code Style & Guidelines

### Java/Spring Services
- Use Java 21 features (records, sealed classes, pattern matching)
- Follow Spring Boot best practices: constructor injection, immutable configurations
- Store properties in `src/main/resources/application.yml` (environment-specific: `application-local.yml`, `application-gcp.yml`)
- All services must include a `Dockerfile` at the root
- Use `./gradlew` (checked-in wrapper) for all Gradle tasks

### Frontend (React/TypeScript)
- Enforce strict TypeScript (no `any` types)
- Use React hooks; avoid class components
- Place API clients in `src/api/` directory
- Use Vite for dev server and bundling
- Store environment variables in `.env.local` (not committed)


### Configuration & Secrets
- Use environment variables for all runtime configuration
- YAML format for K8s and application configs
- Secrets in `.env` files (`.gitignore` them)
- Keep Dockerfiles and docker-compose.yml minimal and production-ready

## Testing
- **Before committing**: `./gradlew test` (services), `npm test` (frontend)
- **Write tests** for API endpoints and business logic
- **Integration tests** for service-to-service communication
- Avoid mocking external services unless testing error handling

## CI/CD & Deployment
- **GitHub Actions**: Workflows in `.github/workflows/`
  - `ci.yml`: Runs backend tests and frontend lint/build on every PR/push.
  - `deploy.yml`: Deploys to GCP Cloud Run on push to `main`.
- **Required GitHub Secrets**:
  - `GCP_PROJECT_ID`: Your Google Cloud Project ID.
  - `GCP_CREDENTIALS`: JSON Service Account key with Cloud Run Admin, Artifact Registry Admin, and Storage Admin roles.
  - `JWT_SECRET`: (Optional) Secret key for JWT signing. Defaults to "none".
  - `APP_AUTH_REQUIRED`: (Optional) "true" or "false". Defaults to "true".
  - `GOOGLE_CLIENT_ID`: (Optional) Google OAuth2 Client ID. Defaults to "none".
  - `GOOGLE_CLIENT_SECRET`: (Optional) Google OAuth2 Client Secret. Defaults to "none".
- **Deployment logic**:
  1. Build/Push backend images to Artifact Registry.
  2. Deploy backend services to get their URLs.
  3. Build/Push frontend image with backend URLs as build args.
  4. Deploy frontend and update auth-service with the final frontend URL.

## Git Workflow
- **Commit messages**: Use conventional format (`feat:`, `fix:`, `refactor:`, `docs:`)
- **Branching**: Create feature branches from `main` (`git checkout -b feature/description`)
- **Merging**: Prefer squash commits for clean history
- **Inclusion**: Always include tests and docs with code changes

## Important Notes & Gotchas
- **Java 21 required**: Verify with `java -version`; failing builds usually indicate version mismatch
- **Gradle permissions**: If `./gradlew` fails, run `chmod +x gradlew` in the service directory
- **JWT validation**: Auth-service signs tokens; downstream services validate via `jwt-common` library
- **CORS setup**: Frontend runs on `localhost:5173`; ensure backend allows this origin in development
- **Database**: CloudSQL requires GCP credentials for production; use local H2/SQL for local development
- **Kind cluster**: Use `skaffold dev` for auto-sync or manually run `kubectl apply` after Docker builds

## Recommended Development Workflow
1. **Explore**: Ask Claude to read relevant service code or architecture
2. **Plan**: Describe the feature before implementing
3. **Implement**: Write code, run tests, verify locally
4. **Test integration**: Deploy to Kind cluster and test end-to-end
5. **Deploy**: Use Terraform for GCP or `kubectl` for Kind

## Implementation Checklist

- [ ] Domain model free of framework dependencies
- [ ] Clear bounded contexts defined
- [ ] Comprehensive test coverage (>80%)
- [ ] All external calls protected with circuit breakers
- [ ] Distributed tracing implemented
- [ ] Structured logging with correlation IDs
- [ ] Health checks configured
- [ ] Graceful shutdown implemented
- [ ] Security scans in CI/CD
- [ ] Auto-scaling configured
- [ ] Monitoring and alerting set up
- [ ] Database migrations automated (Flyway/Liquibase)
- [ ] API versioning strategy defined
- [ ] Rate limiting implemented
- [ ] Documentation up to date


## Conclusion

This architecture provides a solid foundation for building production-ready, cloud-native microservices with:
- Clean domain-driven design
- Comprehensive observability
- High availability and scalability
- Resilience patterns
- Security best practices
- Automated testing and deployment

Adapt these guidelines to your specific business requirements while maintaining the core principles of clean architecture and cloud-native design.