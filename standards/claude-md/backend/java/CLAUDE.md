# Java Backend Standards

Read `../../CLAUDE.md` first. This file extends those principles for Java services built with Spring Boot.

---

## Language & Runtime

- **Java 21+** is the minimum. Java 25 is preferred for new services.
- Use modern Java features. They exist to make code more correct and expressive.
- **Do not use deprecated APIs.** If you encounter one, fix it in the same PR.

### Use These Java Features

| Feature | When to use |
|---|---|
| Records | Immutable DTOs, value objects, response/request shapes |
| Sealed classes + pattern matching | Domain type hierarchies, result types, discriminated unions |
| Virtual threads (`Thread.ofVirtual`) | High-concurrency I/O-bound workloads; replaces reactive WebFlux in most cases |
| Text blocks | Multi-line SQL, JSON, or YAML literals in test fixtures |
| Switch expressions | Exhaustive matching on sealed types or enums |
| `Optional` | Return type for nullable domain results — never use `null` as a return value |

```java
// GOOD — record for immutable DTO
public record CreateOrderRequest(
    @NotBlank String customerId,
    @NotEmpty List<OrderLineItem> items,
    @NotNull Currency currency
) {}

// GOOD — sealed type for domain result
public sealed interface OrderResult
    permits OrderResult.Created, OrderResult.Rejected {

  record Created(Order order) implements OrderResult {}
  record Rejected(String reason) implements OrderResult {}
}

// GOOD — exhaustive switch on sealed type
return switch (result) {
    case OrderResult.Created c  -> ResponseEntity.status(201).body(toDto(c.order()));
    case OrderResult.Rejected r -> ResponseEntity.unprocessableEntity()
                                                  .body(problemDetail(r.reason()));
};
```

### Avoid These

- `null` as a return value from public methods. Use `Optional<T>` or a sealed result type.
- `instanceof` checks without pattern matching (Java < 16 style).
- Mutable data classes with setters. Prefer records or builders.
- `@Data` from Lombok on domain objects — it generates `equals`/`hashCode` based on all fields, which breaks aggregate identity semantics. Use `@Value` or plain records.
- Raw types. Generics must always be fully parameterised.

---

## Spring Boot Standards

### Version and Setup

- **Spring Boot 3.4+** (tracks Spring Framework 6.2+).
- Use the Spring Initializer or the project archetype. Do not create projects manually.
- Gradle is the build tool. Maven is only used for legacy services that are not worth migrating.

### Dependency Injection

**Constructor injection only.** No `@Autowired` on fields. No `@Autowired` on setters (unless Spring Boot's `@ConfigurationProperties` binding requires it).

```java
// BAD — field injection hides dependencies and makes testing hard
@Service
public class OrderService {
    @Autowired
    private OrderRepository repository;
}

// GOOD — constructor injection
@Service
public class OrderService {
    private final OrderRepository repository;
    private final EventPublisher events;

    public OrderService(OrderRepository repository, EventPublisher events) {
        this.repository = repository;
        this.events = events;
    }
}
```

For Spring, use `@RequiredArgsConstructor` from Lombok on the class if there are many dependencies — but only as a code-saving shortcut, not a different pattern.

### Configuration

- All configuration lives in `application.yml`. No `application.properties`.
- Use `@ConfigurationProperties` with validated POJO classes. Do not use `@Value` for anything but the simplest single-field injection.
- Environment-specific configuration uses Spring profiles: `application-dev.yml`, `application-prod.yml`.
- **No secrets in YAML files.** Reference secrets via environment variables that are populated by the secrets manager.

```yaml
# application.yml
app:
  payments:
    provider-url: ${PAYMENTS_PROVIDER_URL}   # injected from env / secret manager
    timeout-seconds: 10
    max-retries: 3
```

```java
@ConfigurationProperties(prefix = "app.payments")
@Validated
public record PaymentsConfig(
    @NotBlank String providerUrl,
    @Positive int timeoutSeconds,
    @Positive int maxRetries
) {}
```

### Profiles

| Profile | Purpose |
|---|---|
| `default` | Local development |
| `dev` | Deployed dev environment |
| `staging` | Staging environment |
| `prod` | Production |
| `test` | Overrides for integration tests (Testcontainers DSNs, etc.) |

Do not use profiles to switch core business logic. Profiles are for infrastructure configuration only.

### Actuator

Enable Spring Boot Actuator. Expose:
- `/actuator/health/liveness` — used by Kubernetes liveness probe
- `/actuator/health/readiness` — used by Kubernetes readiness probe
- `/actuator/metrics` — Prometheus scraping
- `/actuator/info` — build info

Do **not** expose `env`, `configprops`, `beans`, or `heapdump` on public endpoints.

---

## Clean Architecture

The project follows hexagonal (ports and adapters) architecture. The three layers are strictly enforced by ArchUnit tests.

### Layer Rules

```
domain/
  No Spring annotations except @DomainEvent (custom)
  No JPA / persistence annotations
  No Jackson / serialisation annotations
  Pure Java — testable without Spring context

application/
  Depends on domain only
  Defines ports (interfaces): OrderRepository, EventPublisher, PaymentGateway
  Contains use cases / application services
  Spring @Service is allowed here

infrastructure/
  Depends on application and domain
  Contains adapters: JpaOrderRepository, KafkaEventPublisher, HttpPaymentGateway
  Spring @Repository, @Component, JPA entities live here
  Never imported by domain or application

api/
  Depends on application only (calls use cases via ports)
  Contains @RestController, request/response DTOs, @ExceptionHandler
```

Enforce with ArchUnit:

```java
@AnalyzeClasses(packages = "com.acme.orders")
class ArchitectureTest {

    @ArchTest
    ArchRule domainHasNoDependencies =
        noClasses().that().resideInAPackage("..domain..")
                   .should().dependOnClassesThat()
                   .resideInAnyPackage("..infrastructure..", "..api..",
                                       "org.springframework..")
                   .as("Domain layer must not depend on Spring or infra adapters");
}
```

---

## Domain-Driven Design

### Aggregates

- Aggregates are the consistency boundary. All state changes go through the aggregate root.
- Identity is meaningful — use a typed `OrderId` value object, not a raw `UUID`.
- Aggregates publish domain events; they do not call external services directly.

```java
public class Order {
    private final OrderId id;
    private OrderStatus status;
    private final List<OrderLineItem> items;
    private final List<DomainEvent> domainEvents = new ArrayList<>();

    public OrderResult confirm(PaymentConfirmation payment) {
        if (this.status != OrderStatus.PENDING) {
            return new OrderResult.Rejected("Order is not in PENDING status");
        }
        this.status = OrderStatus.CONFIRMED;
        domainEvents.add(new OrderConfirmedEvent(this.id, payment.transactionId()));
        return new OrderResult.Created(this);
    }

    public List<DomainEvent> pullDomainEvents() {
        var events = List.copyOf(domainEvents);
        domainEvents.clear();
        return events;
    }
}
```

### Value Objects

- Immutable. Override `equals` and `hashCode` based on value (records handle this).
- Validate invariants in the constructor. Throw `IllegalArgumentException` for invalid values.

```java
public record Money(BigDecimal amount, Currency currency) {
    public Money {
        Objects.requireNonNull(amount, "amount must not be null");
        Objects.requireNonNull(currency, "currency must not be null");
        if (amount.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("Money amount cannot be negative");
        }
        amount = amount.setScale(2, RoundingMode.HALF_UP);
    }
}
```

### Repositories

- Repository interfaces are defined in `application/` (ports), implemented in `infrastructure/`.
- Return domain objects, not JPA entities. Map at the infrastructure layer boundary.
- Methods are semantically named after domain intent: `findActiveOrdersByCustomer`, not `findByCustomerIdAndStatusNotIn`.

---

## Testing

### Unit Tests

- Test domain logic and application services without Spring context.
- Mock at ports (interfaces), never at concrete infrastructure classes.
- Use `@ExtendWith(MockitoExtension.class)` for Mockito. Do not use `@SpringBootTest` for unit tests.

```java
@ExtendWith(MockitoExtension.class)
class ConfirmOrderUseCaseTest {

    @Mock OrderRepository orders;
    @Mock EventPublisher events;
    @InjectMocks ConfirmOrderUseCase useCase;

    @Test
    void should_publish_OrderConfirmed_event_when_order_is_pending() {
        var order = pendingOrder();
        when(orders.findById(order.id())).thenReturn(Optional.of(order));

        useCase.confirm(order.id(), validPaymentConfirmation());

        verify(events).publish(argThat(e -> e instanceof OrderConfirmedEvent));
    }
}
```

### Integration Tests

- Use `@SpringBootTest` + Testcontainers for persistence and messaging tests.
- Use `@DataJpaTest` for repository tests. Use `@WebMvcTest` for controller tests.
- Do not use H2 as a test database. Use Testcontainers with the real database engine.

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = NONE)
@Testcontainers
class OrderJpaRepositoryTest {

    @Container
    static PostgreSQLContainer<?> postgres =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void overrideProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
    }

    // ...
}
```

### Contract Tests (Pact)

- Every service that consumes an API writes Pact consumer tests.
- Every service that provides an API runs Pact provider verification in CI.
- Pacts are published to a Pact Broker on every main branch build.

---

## Persistence

### JPA / Hibernate

- JPA entities live in `infrastructure/`. They are never exposed to the domain or API layers.
- Use `spring.jpa.open-in-view=false` always. Open Session in View is an anti-pattern.
- Use database migrations (Flyway). Never let Hibernate manage the schema (`ddl-auto=validate` in production; `none` with Flyway in all environments).
- Avoid `FetchType.EAGER`. Default to `LAZY`. Eagerly fetch only with explicit `JOIN FETCH` in queries when needed.
- Use `@Transactional` only on application service methods, not repository methods.

```yaml
# application.yml
spring:
  jpa:
    open-in-view: false
    hibernate:
      ddl-auto: validate
  flyway:
    enabled: true
    locations: classpath:db/migration
```

### Query Performance

- Review `EXPLAIN ANALYZE` output for all non-trivial queries during code review.
- Add database indexes for all foreign keys and frequently filtered columns.
- Paginate all list queries. Never return unbounded result sets.

---

## Resilience

Use Resilience4j. Configure all instances in `application.yml`, not programmatically.

```yaml
resilience4j:
  circuitbreaker:
    instances:
      payments-gateway:
        slidingWindowSize: 10
        failureRateThreshold: 50
        waitDurationInOpenState: 30s
        permittedNumberOfCallsInHalfOpenState: 3
  retry:
    instances:
      payments-gateway:
        maxAttempts: 3
        waitDuration: 500ms
        retryExceptions:
          - java.io.IOException
          - org.springframework.web.client.ResourceAccessException
  timelimiter:
    instances:
      payments-gateway:
        timeoutDuration: 5s
```

- Wrap **all** external service calls (HTTP, gRPC, message broker) with a circuit breaker.
- Configure retries only for **idempotent** operations. Never retry a non-idempotent write without an idempotency key.
- Expose circuit breaker state as a metric. Alert when a circuit opens in production.

---

## Logging and Error Handling

### Structured Logging

Use SLF4J with Logback. Output JSON in all deployed environments.

```java
// GOOD — structured log with context
log.info("Order confirmed",
    kv("orderId", order.id()),
    kv("customerId", order.customerId()),
    kv("amount", order.total().amount()),
    kv("currency", order.total().currency()));

// BAD — unstructured, hard to query
log.info("Order " + orderId + " confirmed by customer " + customerId);
```

Log levels:
- `ERROR` — unexpected failures requiring operator attention
- `WARN` — recoverable problems, degraded operation
- `INFO` — significant business events (order created, payment processed)
- `DEBUG` — technical detail for troubleshooting (disabled in production)
- `TRACE` — very verbose; never enabled in production

### Exception Hierarchy

```
ApplicationException (base, runtime)
  DomainException
    ValidationException      (HTTP 422)
    BusinessRuleViolation    (HTTP 409)
    EntityNotFoundException  (HTTP 404)
  InfrastructureException
    ExternalServiceException (HTTP 502)
    PersistenceException     (HTTP 500)
```

### Global Exception Handler

```java
@RestControllerAdvice
class GlobalExceptionHandler {

    @ExceptionHandler(EntityNotFoundException.class)
    ResponseEntity<ProblemDetail> handleNotFound(EntityNotFoundException ex) {
        var problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setProperty("correlationId", MDC.get("correlationId"));
        return ResponseEntity.status(404).body(problem);
    }

    @ExceptionHandler(ValidationException.class)
    ResponseEntity<ProblemDetail> handleValidation(ValidationException ex) {
        var problem = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_ENTITY,
            "Validation failed");
        problem.setProperty("errors", ex.getErrors());
        return ResponseEntity.status(422).body(problem);
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ProblemDetail> handleUnexpected(Exception ex, HttpServletRequest req) {
        log.error("Unhandled exception for request {}", req.getRequestURI(), ex);
        var problem = ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR,
            "An unexpected error occurred");
        problem.setProperty("correlationId", MDC.get("correlationId"));
        return ResponseEntity.status(500).body(problem);
    }
}
```

---

## Observability

- Use `micrometer-tracing-bridge-otel` + OpenTelemetry Java agent for traces and metrics.
- Add `traceId` and `correlationId` to MDC at the HTTP filter level.
- Expose custom business metrics via `MeterRegistry`.

```java
@Component
class OrderMetrics {
    private final Counter ordersCreated;
    private final Counter ordersRejected;
    private final Timer orderProcessingTime;

    OrderMetrics(MeterRegistry registry) {
        ordersCreated = registry.counter("orders.created.total");
        ordersRejected = registry.counter("orders.rejected.total",
            "reason", "validation_failed");
        orderProcessingTime = registry.timer("orders.processing.duration");
    }
}
```

---

## Build Standards (Gradle)

```groovy
// build.gradle.kts — required plugins
plugins {
    id("org.springframework.boot")
    id("io.spring.dependency-management")
    id("checkstyle")
    id("com.github.spotbugs")
    id("org.owasp.dependencycheck")
    id("jacoco")
}

// Required tasks to pass in CI
tasks.check {
    dependsOn("jacocoTestCoverageVerification")
    dependsOn("dependencyCheckAnalyze")
    dependsOn("spotbugsMain")
}

// Coverage minimum
jacocoTestCoverageVerification {
    violationRules {
        rule {
            limit {
                minimum = "0.80".toBigDecimal()
            }
        }
    }
}
```

---

## Related Standards

- `../../CLAUDE.md` — Root engineering principles
- `../../api/CLAUDE.md` — API design (controllers, DTOs, versioning)
- `standards/overall/tech-stack.md` — Approved Java libraries and frameworks
- `standards/detailed/microservices.md` — Microservice decomposition principles
