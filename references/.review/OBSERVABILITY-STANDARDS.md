# Observability Standards

Standards for metrics, tracing, logging, and alerting.

---

## Three Pillars of Observability

| Pillar | Purpose | Tools |
|--------|---------|-------|
| Metrics | Aggregate numerical data | Prometheus, Grafana |
| Traces | Request flow across services | OpenTelemetry, Jaeger |
| Logs | Event records | Structured JSON, Loki/ELK |

All three must be correlated via trace ID.

---

## OpenTelemetry Integration

### Dependencies
```gradle
implementation platform("io.opentelemetry:opentelemetry-bom:1.34.1")
implementation 'io.opentelemetry:opentelemetry-api'
implementation 'io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter'
```

### Configuration
```yaml
management:
  otlp:
    metrics:
      export:
        enabled: true
        url: http://otel-collector:4318/v1/metrics
    tracing:
      endpoint: http://otel-collector:4318/v1/traces

  tracing:
    sampling:
      probability: 1.0  # 100% in non-prod, lower in prod

  metrics:
    distribution:
      percentiles-histogram:
        http.server.requests: true
```

### Custom Instrumentation
```java
@Service
public class OrderService {

    private final Tracer tracer;
    private final Meter meter;
    private final Counter ordersCreated;
    private final LongHistogram orderProcessingTime;

    public OrderService(OpenTelemetry openTelemetry) {
        this.tracer = openTelemetry.getTracer("order-service");
        this.meter = openTelemetry.getMeter("order-service");

        this.ordersCreated = meter.counterBuilder("orders.created")
            .setDescription("Number of orders created")
            .setUnit("1")
            .build();

        this.orderProcessingTime = meter.histogramBuilder("order.processing.duration")
            .setDescription("Order processing duration")
            .setUnit("ms")
            .ofLongs()
            .build();
    }

    public Order createOrder(CreateOrderCommand command) {
        Span span = tracer.spanBuilder("createOrder")
            .setAttribute("customer.id", command.customerId().toString())
            .startSpan();

        long startTime = System.currentTimeMillis();

        try (Scope scope = span.makeCurrent()) {
            Order order = processOrder(command);
            ordersCreated.add(1, Attributes.of(
                AttributeKey.stringKey("status"), "success"
            ));
            return order;
        } catch (Exception e) {
            span.recordException(e);
            span.setStatus(StatusCode.ERROR, e.getMessage());
            ordersCreated.add(1, Attributes.of(
                AttributeKey.stringKey("status"), "error"
            ));
            throw e;
        } finally {
            orderProcessingTime.record(
                System.currentTimeMillis() - startTime
            );
            span.end();
        }
    }
}
```

---

## Structured Logging

### Format
All logs must be structured JSON with consistent fields:

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class OrderProcessor {
    private static final Logger log = LoggerFactory.getLogger(OrderProcessor.class);

    public void process(Order order) {
        log.atInfo()
            .addKeyValue("orderId", order.getId())
            .addKeyValue("customerId", order.getCustomerId())
            .addKeyValue("amount", order.getTotalAmount())
            .addKeyValue("action", "order.processing.started")
            .log("Processing order");
    }
}
```

### Required Fields
| Field | Description | Example |
|-------|-------------|---------|
| timestamp | ISO 8601 format | 2024-01-15T10:30:00Z |
| level | Log level | INFO, WARN, ERROR |
| service | Service name | order-service |
| traceId | Distributed trace ID | abc123def456 |
| spanId | Current span ID | 789xyz |
| message | Human-readable message | Processing order |

### Log Levels
| Level | Use For |
|-------|---------|
| ERROR | Failures requiring immediate attention |
| WARN | Unexpected but handled conditions |
| INFO | Business events, request/response |
| DEBUG | Development troubleshooting |

### Logback Configuration
```xml
<configuration>
  <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <includeMdcKeyName>traceId</includeMdcKeyName>
      <includeMdcKeyName>spanId</includeMdcKeyName>
    </encoder>
  </appender>

  <root level="INFO">
    <appender-ref ref="JSON"/>
  </root>
</configuration>
```

---

## Metrics

### Metric Types
| Type | Use For | Example |
|------|---------|---------|
| Counter | Cumulative totals | requests_total |
| Gauge | Current values | active_connections |
| Histogram | Distributions | request_duration_seconds |

### Required Metrics
```yaml
# Application Metrics (auto-instrumented)
http_server_requests_seconds_count  # Request count
http_server_requests_seconds_sum    # Total duration
http_server_requests_seconds_bucket # Duration histogram

# JVM Metrics
jvm_memory_used_bytes
jvm_gc_pause_seconds
jvm_threads_live

# Custom Business Metrics
orders_created_total{status="success|error"}
order_processing_duration_seconds
cart_items_count
payment_attempts_total{result="success|failed|timeout"}
```

### Prometheus Configuration
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,metrics,prometheus,info
  metrics:
    export:
      prometheus:
        enabled: true
    tags:
      application: ${spring.application.name}
      environment: ${ENVIRONMENT:local}
```

---

## SLI/SLO Definition

### Service Level Indicators (SLIs)
```yaml
# Availability SLI
sum(rate(http_server_requests_seconds_count{status!~"5.."}[5m]))
/
sum(rate(http_server_requests_seconds_count[5m]))

# Latency SLI (p99 < 500ms)
histogram_quantile(0.99,
  sum(rate(http_server_requests_seconds_bucket[5m])) by (le)
) < 0.5
```

### Service Level Objectives (SLOs)
| Service | Availability | Latency (p99) | Error Rate |
|---------|--------------|---------------|------------|
| API Gateway | 99.9% | < 100ms | < 0.1% |
| Order Service | 99.5% | < 500ms | < 1% |
| Catalog Service | 99.5% | < 200ms | < 1% |

### Error Budget
```
Error Budget = 1 - SLO
Monthly Budget = Error Budget × Minutes in Month

Example: 99.5% availability
Error Budget = 0.5%
Monthly Budget = 0.005 × 43,200 = 216 minutes of downtime
```

---

## Alerting

### Alert Rules
```yaml
groups:
  - name: order-service
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
          /
          sum(rate(http_server_requests_seconds_count[5m]))
          > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanizePercentage }}"
          runbook: "https://runbooks.example.com/high-error-rate"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_server_requests_seconds_bucket[5m])) by (le, service)
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency on {{ $labels.service }}"
          description: "P99 latency is {{ $value | humanizeDuration }}"

      - alert: CircuitBreakerOpen
        expr: resilience4j_circuitbreaker_state{state="open"} > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker open for {{ $labels.name }}"

      - alert: HighMemoryUsage
        expr: |
          jvm_memory_used_bytes{area="heap"}
          /
          jvm_memory_max_bytes{area="heap"}
          > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High heap memory usage"
```

### Alert Severity
| Severity | Response Time | Action |
|----------|--------------|--------|
| Critical | < 15 min | Page on-call immediately |
| Warning | < 1 hour | Notify team channel |
| Info | Next business day | Review in standup |

---

## Dashboards

### Required Dashboards
1. **Service Overview**
   - Request rate
   - Error rate
   - Latency percentiles (p50, p95, p99)
   - Availability

2. **JVM Dashboard**
   - Heap usage
   - GC pauses
   - Thread count
   - CPU usage

3. **Business Metrics**
   - Orders per minute
   - Cart abandonment rate
   - Payment success rate

4. **Infrastructure**
   - Pod count and restarts
   - CPU/memory utilization
   - Network I/O

### Dashboard as Code
```yaml
# Grafana dashboard provisioning
apiVersion: 1
providers:
  - name: default
    folder: Services
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

---

## Distributed Tracing

### Trace Context Propagation
Automatically propagated via OpenTelemetry:
- HTTP headers: `traceparent`, `tracestate`
- Message headers for async communication

### Manual Span Creation
```java
public void processPayment(Payment payment) {
    Span span = tracer.spanBuilder("processPayment")
        .setSpanKind(SpanKind.INTERNAL)
        .setAttribute("payment.id", payment.getId())
        .setAttribute("payment.amount", payment.getAmount())
        .startSpan();

    try (Scope scope = span.makeCurrent()) {
        // Processing logic
        span.addEvent("Payment validated");

        callExternalService();

        span.addEvent("Payment submitted");
    } finally {
        span.end();
    }
}
```

### Async Trace Propagation
```java
// Propagate context to async operations
Context context = Context.current();
executor.submit(() -> {
    try (Scope scope = context.makeCurrent()) {
        // Async work with correct trace context
    }
});

// Propagate to message headers
@Bean
public ProducerFactory<String, Object> producerFactory() {
    return new DefaultKafkaProducerFactory<>(configs,
        new StringSerializer(),
        new JsonSerializer<>(),
        true); // Enable tracing
}
```

---

## Health Checks

### Spring Boot Actuator
```java
@Component
public class DatabaseHealthIndicator implements HealthIndicator {

    private final DataSource dataSource;

    @Override
    public Health health() {
        try (Connection conn = dataSource.getConnection()) {
            if (conn.isValid(5)) {
                return Health.up()
                    .withDetail("database", "available")
                    .build();
            }
        } catch (SQLException e) {
            return Health.down()
                .withException(e)
                .build();
        }
        return Health.down().build();
    }
}
```

### Kubernetes Probes
```yaml
livenessProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
  initialDelaySeconds: 20
  periodSeconds: 5
```

---

## Runbooks

### Runbook Requirements
Every alert must link to a runbook containing:
1. Alert meaning and impact
2. Diagnostic steps
3. Remediation procedures
4. Escalation path
5. Post-incident actions

### Example Runbook Template
```markdown
# High Error Rate

## Alert Meaning
Error rate exceeds 5% of requests for more than 2 minutes.

## Impact
Users may experience failures when placing orders.

## Diagnostic Steps
1. Check Grafana dashboard for error breakdown
2. Review logs: `kubectl logs -l app=order-service --tail=100`
3. Check dependent services status
4. Review recent deployments

## Remediation
1. If recent deployment: rollback
2. If dependency failure: check circuit breaker status
3. If resource exhaustion: scale horizontally

## Escalation
- Slack: #order-service-alerts
- PagerDuty: Order Service team
```
