# Architecture Patterns

Standards for implementing core architectural patterns in cloud-native systems.

---

## Domain-Driven Design (DDD)

### Strategic Patterns

#### Bounded Contexts
- Each microservice represents one bounded context
- Define ubiquitous language per context
- Use context mapping for inter-service relationships

#### Context Mapping Types
| Pattern | Use When |
|---------|----------|
| Partnership | Two teams cooperate closely |
| Shared Kernel | Multiple contexts share a small model |
| Customer-Supplier | Upstream/downstream relationship |
| Conformist | Downstream adopts upstream model |
| Anti-corruption Layer | Protect from external model pollution |
| Open Host Service | Expose well-defined protocol |
| Published Language | Documented interchange format |

### Tactical Patterns

#### Aggregates
```java
@Entity
public class Order {
    @Id
    private OrderId id;
    private CustomerId customerId;
    private OrderStatus status;

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderLine> orderLines;

    // Enforce invariants within aggregate boundary
    public void addOrderLine(Product product, int quantity) {
        validateOrderLine(product, quantity);
        orderLines.add(new OrderLine(product, quantity));
        registerEvent(new OrderLineAdded(id, product.getId(), quantity));
    }
}
```

#### Value Objects
```java
public record OrderId(UUID value) {
    public OrderId {
        Objects.requireNonNull(value, "OrderId cannot be null");
    }

    public static OrderId generate() {
        return new OrderId(UUID.randomUUID());
    }
}

public record Money(BigDecimal amount, Currency currency) {
    public Money {
        if (amount.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("Amount cannot be negative");
        }
        Objects.requireNonNull(currency);
    }

    public Money add(Money other) {
        requireSameCurrency(other);
        return new Money(amount.add(other.amount), currency);
    }
}
```

#### Domain Events
```java
public sealed interface DomainEvent permits OrderCreated, OrderShipped, OrderCancelled {
    Instant occurredAt();
    String aggregateId();
}

public record OrderCreated(
    OrderId orderId,
    CustomerId customerId,
    Instant occurredAt
) implements DomainEvent {
    @Override
    public String aggregateId() {
        return orderId.value().toString();
    }
}
```

#### Domain Services
Use when logic doesn't naturally belong to a single entity:
```java
public class PricingService {
    public Money calculateTotal(Order order, DiscountPolicy discountPolicy) {
        Money subtotal = order.calculateSubtotal();
        Money discount = discountPolicy.apply(subtotal, order.getCustomerId());
        return subtotal.subtract(discount);
    }
}
```

---

## Hexagonal Architecture (Ports & Adapters)

### Overview
Hexagonal architecture separates core business logic from external concerns through ports (interfaces) and adapters (implementations).

### Structure of a Hexagonal service
```
src/main/java/
├── domain/              # Core business logic (NO framework dependencies)
│   ├── model/           # Entities, Value Objects, Aggregates
│   ├── repository/      # Repository interfaces (ports)
│   ├── service/         # Domain services
│   └── event/           # Domain events
├── application/         # Application services and use cases
│   ├── command/         # Command handlers (write operations)
│   ├── query/           # Query handlers (read operations)
│   └── dto/             # Data transfer objects
├── infrastructure/      # Technical implementations (adapters)
│   ├── persistence/     # Database implementations
│   ├── messaging/       # Event publishing/consuming
│   ├── cache/           # Caching implementations
│   └── external/        # External service clients
└── api/                 # Inbound adapters
    ├── rest/            # REST controllers
    └── graphql/         # GraphQL resolvers
```

### Rules
1. **Domain has zero dependencies** on frameworks or infrastructure
2. **Ports are interfaces** defined in the domain layer
3. **Adapters implement ports** and live in infrastructure
4. **Dependencies point inward** toward the domain

---


## Event-Driven Architecture

### Event Types
| Type | Purpose | Example |
|------|---------|---------|
| Domain Events | Record business facts | `OrderPlaced`, `PaymentReceived` |
| Integration Events | Cross-service communication | `OrderCreatedIntegrationEvent` |
| Command Events | Request action | `ProcessPaymentCommand` |

### Event Design
```java
// Integration event with schema versioning
public record OrderCreatedEvent(
    @JsonProperty("event_id") UUID eventId,
    @JsonProperty("event_type") String eventType,
    @JsonProperty("event_version") int version,
    @JsonProperty("timestamp") Instant timestamp,
    @JsonProperty("payload") OrderPayload payload
) {
    public static final String EVENT_TYPE = "order.created";
    public static final int CURRENT_VERSION = 1;
}
```

### Patterns

#### Outbox Pattern
Ensure reliable event publishing with transactional outbox:
```java
@Transactional
public Order createOrder(CreateOrderCommand command) {
    Order order = orderFactory.create(command);
    orderRepository.save(order);

    // Store event in outbox table (same transaction)
    outboxRepository.save(new OutboxEvent(
        order.getId(),
        "OrderCreated",
        serialize(order.toDomainEvent())
    ));

    return order;
}
```

#### Saga Pattern
Coordinate distributed transactions:
```
OrderSaga:
  1. CreateOrder -> OrderCreated
  2. ReserveInventory -> InventoryReserved | InventoryFailed
  3. ProcessPayment -> PaymentProcessed | PaymentFailed
  4. ConfirmOrder -> OrderConfirmed

Compensations:
  - PaymentFailed -> ReleaseInventory
  - InventoryFailed -> CancelOrder
```

#### Dead Letter Queue
Handle failed message processing:
```yaml
spring:
  cloud:
    stream:
      bindings:
        orderProcessor-in-0:
          destination: orders
          group: order-service
          consumer:
            max-attempts: 3
            back-off-initial-interval: 1000
            back-off-max-interval: 10000
            dlq-name: orders.dlq
```

---

## CQRS (Command Query Responsibility Segregation)

### When to Use
- Complex domains with different read/write patterns
- High read-to-write ratio
- Need for optimized read models with simpler structure and queries
- Event sourcing systems

### Structure
```
├── command/
│   ├── CreateOrderCommand.java
│   ├── CreateOrderCommandHandler.java
│   └── OrderCommandRepository.java  # Write-optimized
├── query/
│   ├── GetOrderQuery.java
│   ├── GetOrderQueryHandler.java
│   ├── OrderReadModel.java          # Denormalized for reads
│   └── OrderQueryRepository.java    # Read-optimized
```

### Implementation
```java
// Command side - enforces invariants
@Component
public class CreateOrderCommandHandler {
    public OrderId handle(CreateOrderCommand command) {
        Order order = Order.create(command);
        orderRepository.save(order);
        eventPublisher.publish(order.getDomainEvents());
        return order.getId();
    }
}

// Query side - optimized for reads
@Component
public class OrderQueryHandler {
    public OrderReadModel handle(GetOrderQuery query) {
        return orderReadRepository.findById(query.orderId())
            .orElseThrow(() -> new OrderNotFoundException(query.orderId()));
    }
}
```

---

## Resilience Patterns

### Circuit Breaker
```java
@CircuitBreaker(name = "payment-service", fallbackMethod = "paymentFallback")
@Retry(name = "payment-service")
@TimeLimiter(name = "payment-service")
public PaymentResult processPayment(PaymentRequest request) {
    return paymentClient.process(request);
}

private PaymentResult paymentFallback(PaymentRequest request, Exception ex) {
    log.warn("Payment service unavailable, queuing", ex);
    return PaymentResult.queued(request.transactionId());
}
```

### Configuration
```yaml
resilience4j:
  circuitbreaker:
    instances:
      payment-service:
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s
        sliding-window-size: 10
        minimum-number-of-calls: 5

  retry:
    instances:
      payment-service:
        max-attempts: 3
        wait-duration: 500ms
        retry-exceptions:
          - java.util.concurrent.TimeoutException
          - java.net.ConnectException

  bulkhead:
    instances:
      payment-service:
        max-concurrent-calls: 10
        max-wait-duration: 100ms
```

### Resilience Patterns Summary
| Pattern | Purpose | Configuration |
|---------|---------|---------------|
| Circuit Breaker | Stop cascading failures | failure threshold, wait duration |
| Retry | Handle transient failures | max attempts, backoff strategy |
| Bulkhead | Isolate failures | max concurrent calls, queue size |
| Rate Limiter | Control throughput | requests per period |
| Time Limiter | Bound execution time | timeout duration |
