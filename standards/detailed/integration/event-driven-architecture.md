# Event-Driven Architecture (EDA)

Detailed standards for designing, building, and operating event-driven systems in a cloud-native environment.

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Decoupled Services** | Producers and consumers evolve independently — no shared deployment schedule |
| **Scalability** | Consumers scale horizontally based on event backlog, not request rate |
| **Resilience** | Broker absorbs spikes and retains events — consumers recover from downtime without data loss |
| **Auditability** | Immutable event log provides a complete history of what happened and when |
| **Real-time Reactivity** | Systems respond to facts as they occur, not on the next polling cycle |
| **Cross-domain Integration** | Events are the contract between bounded contexts — no shared databases or direct service calls |
| **Extensibility** | New consumers can be added without modifying the producer |

---

## Core Principles

### 1. Events Are Facts, Not Commands
An event records something that happened in the domain. It is immutable and named in the past tense. It does not prescribe what any consumer should do with it.

**What this means:**
- Name events as past-tense business facts: `OrderPlaced`, `PaymentProcessed`, `InventoryReserved`
- Producers have no knowledge of, or dependency on, consumers
- Consumers decide independently how to react to an event
- Never encode intent or expected behavior into event names (e.g., `NotifyCustomer` is a command, not an event)

**Decision guide:**
- "Something happened in my domain" → publish an event
- "I need another service to do something specific" → call it directly (sync) or send a command message

---

### 2. Decouple Producers from Consumers
Producers publish to a broker. Consumers subscribe from the broker. Neither knows about the other. This temporal and structural decoupling is the core value of EDA.

**What this means:**
- Producers never call consumer APIs directly when an event-driven approach is appropriate
- A producer publishes an event and moves on — no waiting for consumer acknowledgment
- Adding a new consumer requires zero changes to the producer
- Schema contracts (not shared code) are the only coupling between producer and consumer

```
┌─────────────┐     event      ┌──────────────┐     event      ┌─────────────┐
│  Order      │ ─────────────▶ │   Message    │ ─────────────▶ │  Payment    │
│  Service    │  (OrderPlaced) │   Broker     │  (OrderPlaced) │  Service    │
└─────────────┘                └──────────────┘                └─────────────┘
                                      │
                                      │ (OrderPlaced)
                                      ▼
                               ┌─────────────┐
                               │  Inventory  │
                               │  Service    │
                               └─────────────┘
```

---

### 3. Design Events for Idempotent Consumption
The broker guarantees at-least-once delivery. Consumers will receive duplicate events. Every consumer must be safe to call multiple times with the same event.

**What this means:**
- Track processed event IDs in a deduplications store (DB table, Redis set)
- Upserts are safer than inserts for state mutations
- Side effects (emails, external API calls) must be guarded by a processed-event check
- Idempotency key = `eventId` or `(aggregateId + eventType + version)`

**Implementation pattern:**
```java
@Transactional
public void handle(OrderPlacedEvent event) {
    if (processedEventRepository.exists(event.eventId())) {
        return; // already handled — safe to ignore
    }
    // process the event
    inventoryService.reserve(event.orderId(), event.lineItems());
    processedEventRepository.markProcessed(event.eventId());
}
```

---

### 4. Guarantee Exactly-Once Publishing with the Outbox Pattern
Never publish directly to the broker inside a business transaction. Network failures between your DB commit and broker publish create ghost events or lost events.

**What this means:**
- Write the event to an `outbox` table in the same DB transaction as the state change
- A relay process reads the outbox and publishes to the broker, then marks the record as published
- The broker receives the event exactly once; consumers handle idempotency for the rest

```
Business Transaction:
  1. UPDATE orders SET status = 'PLACED'
  2. INSERT INTO outbox (event_type, payload) VALUES ('OrderPlaced', {...})
  ── COMMIT ──

Relay Process (async):
  3. SELECT * FROM outbox WHERE published = false
  4. Publish to broker
  5. UPDATE outbox SET published = true
```

```java
@Transactional
public Order placeOrder(PlaceOrderCommand cmd) {
    Order order = Order.create(cmd);
    orderRepository.save(order);

    outboxRepository.save(OutboxEvent.of(
        "OrderPlaced",
        OrderPlacedPayload.from(order)
    ));

    return order; // broker publish happens OUTSIDE this transaction
}
```

---

### 5. Version Event Schemas Explicitly
Event consumers are deployed independently. A producer may update its schema while old consumers are still running. Breaking schema changes must be versioned.

**What this means:**
- Always include `schemaVersion` (integer) in every event envelope
- Use backward-compatible changes only without bumping the version: adding optional fields
- Use forward-compatible changes only without bumping the version: removing fields consumers ignore
- Breaking changes (rename, type change, required field removal) require a new version
- Maintain a schema registry (Confluent, AWS Glue, Azure Schema Registry) for all event schemas
- Run consumer contract tests (Pact) before deploying producer changes

**Standard event envelope:**
```json
{
  "eventId":      "uuid-v4",
  "eventType":    "order.placed",
  "schemaVersion": 1,
  "occurredAt":   "2026-04-21T10:00:00Z",
  "aggregateId":  "order-789",
  "aggregateType":"Order",
  "correlationId":"trace-abc-123",
  "payload": {
    "orderId":    "order-789",
    "customerId": "cust-456",
    "totalAmount": 149.99,
    "currency":   "AUD"
  }
}
```

---

### 6. Use the Right Topology for Each Workflow
Not all EDA workflows are the same. Choreography suits simple independent reactions. Orchestration suits multi-step workflows that require compensation.

**Choreography — decentralized, no coordinator:**
```
OrderPlaced ──▶ InventoryService  (reserves stock)
            └──▶ NotificationService (sends confirmation)
            └──▶ AnalyticsService   (records the event)
```
- Use when: each consumer reacts independently, no cross-step dependencies
- Avoid when: you need visibility into a multi-step workflow as a whole

**Orchestration (Saga) — centralized coordinator:**
```
OrderSaga (Orchestrator)
  1. PlaceOrder     ──▶ OrderService       ──▶ OrderCreated
  2. ReserveStock   ──▶ InventoryService   ──▶ StockReserved | StockFailed
  3. ProcessPayment ──▶ PaymentService     ──▶ PaymentProcessed | PaymentFailed
  4. ConfirmOrder   ──▶ OrderService       ──▶ OrderConfirmed

Compensations:
  PaymentFailed    ──▶ ReleaseStock  ──▶ CancelOrder
  StockFailed      ──▶ CancelOrder
```
- Use when: steps have dependencies, rollback is required, workflow state must be observable
- Frameworks: AWS Step Functions, Azure Durable Functions, Temporal, Axon Framework

---

### 7. Handle Failures Explicitly with Dead Letter Queues
Messages that cannot be processed must not be silently dropped. Route them to a Dead Letter Queue (DLQ) for inspection and replay.

**What this means:**
- Configure max retry attempts with exponential backoff before routing to DLQ
- Monitor DLQ depth as an operational metric — alert when non-zero
- Every DLQ message must retain the original payload and error metadata
- Build a replay mechanism: fix the bug, then replay from DLQ

**Kafka DLQ configuration:**
```yaml
spring:
  kafka:
    consumer:
      enable-auto-commit: false
    listener:
      ack-mode: MANUAL
      concurrency: 3

# Retry + DLQ via Spring Retry Topics
@RetryableTopic(
    attempts = "3",
    backoff = @Backoff(delay = 1000, multiplier = 2.0),
    dltTopicSuffix = ".dlq"
)
@KafkaListener(topics = "orders")
public void handle(OrderPlacedEvent event) { ... }
```

---

### 8. Maintain Ordering Guarantees Where Required
Global ordering is expensive. Partition-level ordering is sufficient for most domain use cases. Design your partition key around business ordering requirements.

**What this means:**
- Use the aggregate ID (e.g., `orderId`) as the Kafka partition key — all events for one order land on the same partition in order
- Do not use a random or hash key when ordering matters within an entity's lifecycle
- Global ordering is almost never required; question any requirement that demands it

| Scenario | Partition Key |
|----------|---------------|
| Order lifecycle events | `orderId` |
| Customer activity events | `customerId` |
| Payment events | `paymentId` |
| Multi-tenant systems | `tenantId + aggregateId` |

---

## Event Design Standards

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Event type (wire) | `{domain}.{entity}.{verb-past-tense}` | `order.payment.processed` |
| Event class (code) | `{Entity}{Verb}Event` | `PaymentProcessedEvent` |
| Topic / subject | `{domain}-{entity}-events` | `order-payment-events` |
| Consumer group | `{service}-{entity}-consumer` | `inventory-order-consumer` |

### What Belongs in an Event Payload
- Include: the aggregate ID, key state at the time of the event, timestamp, version
- Avoid: entire object graphs, data from other bounded contexts, computed fields that can be derived
- Rule of thumb: a consumer should be able to act on the event without fetching additional data for the common case

### Event Granularity
| Too Fine-Grained | Just Right | Too Coarse-Grained |
|-----------------|------------|-------------------|
| `Order.FieldUpdated` | `OrderPlaced`, `OrderShipped` | `OrderChanged` |
| `Customer.EmailChanged` | `CustomerRegistered` | `CustomerUpdated` |
| Hard to react to meaningfully | Maps to a business fact | Consumers must inspect diff to know what happened |

---

## Technology Selection Guide

### Message Broker Comparison

| Concern | Apache Kafka | RabbitMQ | AWS EventBridge | Azure Event Grid |
|---------|-------------|----------|-----------------|-----------------|
| **Best for** | High-throughput event streaming, event sourcing | Task queues, complex routing | AWS-native integrations | Azure-native integrations |
| **Ordering** | Per-partition | Per-queue | Best-effort | Best-effort |
| **Retention** | Configurable (days–forever) | Until consumed | 24 hours | 24 hours |
| **Throughput** | Millions/sec | Thousands/sec | Moderate | Moderate |
| **Consumer model** | Pull (poll) | Push | Push | Push |
| **Schema registry** | Confluent / AWS Glue | N/A | Schema Registry | Schema Registry |
| **Replay** | Yes (offset rewind) | No (once consumed) | No | No |
| **Use in this playbook** | Default for inter-service events | Task/job queuing | AWS integration events | Azure integration events |

### When to Choose What

```
Need event replay or audit log?
  └─ Yes ──▶ Kafka (or Kinesis on AWS)
  └─ No ──▶ Continue

High throughput (>10k events/sec)?
  └─ Yes ──▶ Kafka
  └─ No ──▶ Continue

AWS-native services as producer/consumer?
  └─ Yes ──▶ EventBridge
  └─ No ──▶ Continue

Azure-native services as producer/consumer?
  └─ Yes ──▶ Event Grid
  └─ No ──▶ RabbitMQ or Kafka
```

---

## Patterns Reference

### Outbox Pattern
Atomic event publishing with zero risk of lost events. See [Principle 4](#4-guarantee-exactly-once-publishing-with-the-outbox-pattern).

### Event Sourcing
Store state as a sequence of events rather than a current snapshot.

```
Traditional:  orders table → current_state row (mutable)
Event Sourced: order_events table → append-only log of what happened

Reconstruct state:
  OrderCreated { items: [...], total: 149.99 }
  + OrderShipped { trackingId: "TRK-001" }
  + OrderDelivered { deliveredAt: "2026-04-21" }
  = current Order state (derived by replaying events)
```

**Use when:**
- Audit trail is a first-class requirement
- State at any point in time must be reconstructable
- Business rules need to reason about history

**Avoid when:**
- Simple CRUD with no audit requirements
- Team is not ready for the operational complexity

### CQRS with Event-Driven Read Models
Write side publishes events → Read side consumes events and builds optimized read models.

```
Write Path:                          Read Path:
  Command ──▶ Aggregate ──▶ Event      Event ──▶ Projection ──▶ Read Model
              (save + publish)                    (update)      (query-optimized)
```

### Competing Consumers
Multiple consumer instances read from the same topic/queue, distributing load.

```
Topic: orders (3 partitions)
  Partition 0 ──▶ inventory-service instance A
  Partition 1 ──▶ inventory-service instance B
  Partition 2 ──▶ inventory-service instance C
```

- In Kafka: one partition is owned by one consumer in a consumer group at a time
- Scale consumers up to match the number of partitions (beyond that, instances are idle)

### Change Data Capture (CDC)
Capture database changes as events without modifying application code.

```
Source DB (Postgres)
   │  WAL (Write-Ahead Log)
   ▼
Debezium (CDC connector)
   │  change events
   ▼
Kafka Topic ──▶ downstream consumers
```

**Use when:**
- Integrating with legacy systems that cannot publish events natively
- Synchronizing read models from a write database
- Building a data lake pipeline from operational databases

---

## Operational Standards

| Practice | Requirement |
|----------|-------------|
| Dead Letter Queue | Every consumer topic must have a DLQ configured |
| DLQ alerting | Alert fires when DLQ depth > 0 for > 5 minutes |
| Consumer lag monitoring | Alert on consumer lag > SLA threshold (e.g., 10k messages) |
| Schema registry | All event schemas registered; compatibility mode enforced (BACKWARD_TRANSITIVE) |
| Correlation ID | `correlationId` propagated through all events and logs for distributed tracing |
| Replay capability | Kafka: retention ≥ 7 days; DLQ replay tooling documented in runbook |
| Idempotency testing | Integration tests must verify duplicate-event handling for every consumer |
| Contract tests | Pact or equivalent run in CI before producer deployments |
| Graceful shutdown | Consumers complete in-flight message processing before shutting down |

---

## Observability

### Key Metrics per Consumer
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `consumer_lag` | Messages behind latest offset | > SLA-dependent threshold |
| `processing_error_rate` | Rate of failed message processing | > 1% over 5m |
| `dlq_depth` | Messages in dead letter queue | > 0 for > 5m |
| `processing_latency_p99` | End-to-end processing time | > SLA latency |
| `retry_rate` | Rate of retried messages | Spike indicates systemic issue |

### Correlation ID Propagation
Every event must carry a `correlationId` that traces the originating request across all downstream events and service calls.

```java
// Producer — propagate from inbound trace
OutboxEvent.of("OrderPlaced", payload, traceContext.correlationId());

// Consumer — restore trace context from event
MDC.put("correlationId", event.correlationId());
tracer.startSpanWithId(event.correlationId());
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Event-carried state transfer overload | Huge payloads couple consumer to producer schema | Include only essential fields; consumers fetch additional data if needed |
| Publishing inside a transaction without outbox | Lost events on commit/publish race | Always use the outbox pattern |
| Synchronous reply-over-events | Request/reply via events is complex and fragile | Use synchronous REST/gRPC for query operations |
| Implicit event ordering assumptions | Partitioning may deliver events out of order across partitions | Design consumers to handle out-of-order delivery; use aggregate-keyed partitions |
| Ignoring DLQ messages | Silent data loss | Monitor DLQ, alert immediately, build replay tooling |
| Shared consumer groups across services | Service A and B compete for events meant for both | Each service uses its own consumer group |
| Commands masquerading as events | `SendWelcomeEmail` is a command, not an event | Name events as facts; commands go via direct call or command queue |
| Schema changes without versioning | Consumers break on payload change | Version all events; use a schema registry with compatibility checks |
| Fat events (entire aggregates) | Payload bloat, consumers receive irrelevant data | Lean events with projection-fetching for detail when needed |
