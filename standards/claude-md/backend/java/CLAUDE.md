# Java Backend Standards

Extends ../../CLAUDE.md.

## Versions and libraries
| Area | Standard |
|---|---|
| JDK | 21 minimum; 25 (LTS) for new services |
| Framework | Spring Boot 4.0+ (Spring Framework 7+), generated via Spring Initializr |
| Build | Gradle Kotlin DSL; Maven only for legacy services |
| Persistence | Spring Data JPA/Hibernate, Flyway |
| Resilience | Resilience4j (confirm the starter supports the Boot version in use before upgrading Boot) |
| Telemetry | Micrometer Tracing (`micrometer-tracing-bridge-otel`) + OTLP export; Logback with a JSON encoder (logstash-logback-encoder) |
| Tests | JUnit 5, Mockito, Testcontainers (`@ServiceConnection`), ArchUnit, Pact JVM |

- Virtual threads for blocking I/O (`spring.threads.virtual.enabled: true`); do not adopt WebFlux for new services.
- Return `Optional<T>` or a sealed result type; never `null` from public methods. Records for DTOs and value objects (invariants checked in the compact constructor).
- No Lombok `@Data` on domain types (all-field `equals`/`hashCode` breaks aggregate identity). Prefer records.

## Package layout
`com.acme.<service>.{domain,application,infrastructure,api}` per root layering.
- `domain`: no Spring, JPA or Jackson annotations. Identity is a typed id (`OrderId`), not a raw `UUID`. Aggregates collect domain events and expose `pullDomainEvents()`.
- `application`: ports and use cases; `@Service` and `@Transactional` allowed here, and only here.
- `infrastructure`: JPA entities and Spring Data repositories, mapped to domain objects at the port boundary. Entities never leave this package.
- `api`: controllers, DTOs, `@RestControllerAdvice`; calls `application` only.

Enforced by ArchUnit (`ArchitectureTest`, runs in `check`):
```java
noClasses().that().resideInAPackage("..domain..")
    .should().dependOnClassesThat().resideInAnyPackage(
        "..application..", "..infrastructure..", "..api..", "org.springframework..", "jakarta.persistence..");
noClasses().that().resideInAPackage("..application..")
    .should().dependOnClassesThat().resideInAnyPackage("..infrastructure..", "..api..");
noClasses().that().resideInAPackage("..api..")
    .should().dependOnClassesThat().resideInAPackage("..infrastructure..");
```

## Configuration
- `application.yml` only (no `.properties`). Profiles: `default` (local), `dev`, `staging`, `prod`, `test`. Profiles switch infrastructure, never business logic.
- `@ConfigurationProperties` + `@Validated` records; `@Value` only for a single trivial value. Secrets come from env vars populated by the secrets manager, never from YAML.
- Required settings:
```yaml
spring:
  jpa:
    open-in-view: false
    hibernate.ddl-auto: validate      # schema owned by Flyway
  flyway.locations: classpath:db/migration
  threads.virtual.enabled: true
management:
  endpoint.health:
    probes.enabled: true
    group:
      liveness.additional-path: "server:/health/live"
      readiness.additional-path: "server:/health/ready"
  endpoints.web.exposure.include: health,info,prometheus
```
- Never expose `env`, `configprops`, `beans`, `heapdump`. Permit `/health/**` unauthenticated; keep `/actuator/prometheus` internal.
- `FetchType.LAZY` everywhere; fetch explicitly with `JOIN FETCH`. Paginate every list query; index every foreign key.

## Exception to HTTP mapping
One `@RestControllerAdvice` extending `ResponseEntityExceptionHandler`, producing `ProblemDetail` per root (add `correlationId` from MDC via `setProperty`).

| Exception | Status |
|---|---|
| `ValidationException`, `MethodArgumentNotValidException`, `ConstraintViolationException` | 422 (with `errors[{field,message}]`) |
| `BusinessRuleViolation`, `OptimisticLockingFailureException` | 409 |
| `EntityNotFoundException` | 404 |
| `ExternalServiceException` | 502 |
| `PersistenceException`, anything else | 500 (generic detail; log with stack trace) |

## Tests
- Unit: `@ExtendWith(MockitoExtension.class)`, no Spring context, mocks at ports.
- Slices: `@WebMvcTest` (controllers), `@DataJpaTest` with `@AutoConfigureTestDatabase(replace = NONE)` and a Testcontainers Postgres matching the production major version via `@ServiceConnection`. No H2.
- Pact: provider verification in CI; publish pacts from `main`.

## Resilience
Configure in `application.yml` only (`resilience4j.circuitbreaker|retry|timelimiter.instances.<client>`). Every outbound call (HTTP, gRPC, broker) gets a circuit breaker and timeout. Retry only idempotent calls (or writes carrying an idempotency key).

## Build enforcement (`build.gradle.kts`)
Plugins: `checkstyle`, `com.github.spotbugs`, `org.owasp.dependencycheck`, `jacoco`.
```kotlin
tasks.jacocoTestCoverageVerification {
    violationRules { rule { limit { counter = "BRANCH"; minimum = "0.80".toBigDecimal() } } }
}
tasks.check { dependsOn("jacocoTestCoverageVerification", "dependencyCheckAnalyze", "spotbugsMain") }
```
CI runs `./gradlew check`. Configure `failBuildOnCVSS = 7.0f` for dependency-check, and exclude generated code from coverage.
