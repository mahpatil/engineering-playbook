# Core Observability

Standards for the foundation of observability: the three signals (logs, metrics, traces), OpenTelemetry (OTel) instrumentation, signal correlation, and the golden signals.

---

## What Observability Means

Observability is the ability to **answer questions about a running system from its outputs**, without shipping new code to find the answer. It is not the same as monitoring: monitoring tells you something is wrong; observability lets you ask *why*.

The system is observable when an engineer can reconstruct, from telemetry alone:

- **What** happened (logs/events)
- **Which** requests/users were affected (traces)
- **At what scale / level** (metrics / aggregates)

---

## The Three Signals (Pillars)

| Signal | Answers | Nature | Primary Tooling |
|--------|---------|--------|-----------------|
| **Metrics** | *Is something happening? How much?* | Aggregate numerical data over time | Prometheus, Grafana, cloud-native metrics |
| **Logs** | *What exactly happened for this event?* | Discrete, timestamped event records | ELK, Loki, cloud log stores |
| **Traces** | *What is the path and cost of a request across services?* | Request-scoped, spans with causality | Jaeger, Tempo, APM backends |

> **Newer signals (emerging but not mandatory):** Profiles (continuous profiling — e2e latency attribution) and Events (domain-level business events). Treat them as additive, not a replacement for the three pillars.

---

## Why OpenTelemetry (OTel)

OpenTelemetry is the **industry-standard, vendor-neutral** framework for producing telemetry: a single SDK + auto-instrumentation story that emits all three signals, with a portable pipeline (the Collector) and standard wire protocols (OTLP).

**Non-negotiables:**

1. **Instrument with OTel, never a vendor SDK.** Application code must not import Prometheus, Datadog, New Relic, or cloud-native telemetry SDKs directly.
2. **Emit all three signals** via OTLP to an OpenTelemetry Collector.
3. **Propagate context** (`traceparent`) across every hop — HTTP, gRPC, queues, and databases.
4. **Auto-instrumentation first, manual where it adds domain value.**

---

## OTel Components in Scope

| Component | Role |
|-----------|------|
| **OTel SDK** | In-process library producing spans, metrics, log records |
| **OTel Auto-instrumentation / Agents** | Zero or low-code capture of common frameworks (HTTP server/client, DB, messaging, RPC) |
| **OTel API + Manual instrumentation** | Domain-specific spans, metrics, semantic attributes |
| **OTel Collector** | Agent/gateway that receives, processes, and routes telemetry to backends (see [OTel Collector](./otel-collector.md)) |
| **OTLP** | The standard protocol for exporting (HTTP/gRPC, port 4318 / 4317) |

---

## Instrumentation Standards

### 1. Auto-instrumentation by default

Every service runs the language-appropriate OTel instrumentation:

| Language | Approach |
|----------|----------|
| Java | `opentelemetry-javaagent.jar` (attach at startup) + Micrometer/OTel tracing bridge |
| Python | `opentelemetry-instrumentation` + distro packages |
| Node.js | `@opentelemetry/auto-instrumentations-node` |
| .NET | `OpenTelemetry.Instrumentation.AspNetCore` + hosting bundle |
| Go | `go.opentelemetry.io/auto` + explicit exporters (no runtime agent) |

**Java example (standard stack):**
```yaml
# application.yml
management:
  otlp:
    metrics:
      export:
        enabled: true
        url: http://otel-collector:4318/v1/metrics
    tracing:
      endpoint: http://otel-collector:4318/v1/traces
  metrics:
    export:
      prometheus:
        enabled: false   # prefer OTLP to the Collector, not direct pull
    distribution:
      percentiles-histogram:
        http.server.requests: true
  tracing:
    sampling:
      probability: 1.0   # 100% for dev/QA; tail sampling in prod (see collector doc)
```

### 2. Manual instrumentation where it adds domain value

Add manual spans/metrics only for **business-meaningful** operations that auto-instrumentation cannot express:

```java
@Service
public class OrderService {
    private final Tracer tracer;
    private final Meter meter;
    private final Counter ordersCreated;
    private final DoubleHistogram orderProcessingTime;

    public OrderService(OpenTelemetry otel) {
        this.tracer = otel.getTracer("order-service");
        this.meter  = otel.getMeter("order-service");
        this.ordersCreated = meter.counterBuilder("orders.created.total")
            .setDescription("Orders created")
            .setUnit("1").build();
        this.orderProcessingTime = meter.histogramBuilder("order.processing.duration")
            .setUnit("ms").build();
    }

    public Order createOrder(CreateOrderCommand cmd) {
        Span span = tracer.spanBuilder("createOrder")
            .setAttribute("customer.id", cmd.customerId().toString())
            .startSpan();
        try (var scope = span.makeCurrent()) {
            long t0 = System.currentTimeMillis();
            Order order = processOrder(cmd);
            ordersCreated.add(1, Attributes.of(stringKey("status"), "success"));
            orderProcessingTime.record(System.currentTimeMillis() - t0);
            return order;
        } catch (Exception e) {
            span.recordException(e);
            span.setStatus(StatusCode.ERROR, e.getMessage());
            ordersCreated.add(1, Attributes.of(stringKey("status"), "error"));
            throw e;
        } finally {
            span.end();
        }
    }
}
```

**Rule of thumb:** a salient (named, typed) business event ✚ frequent / expensive / failure-prone operation is a candidate for manual instrumentation. Do not hand-build spans that auto-instrumentation already covers.

### 3. Semantic conventions

Use **OTel semantic conventions** for attribute names (`http.request.method`, `http.response.status_code`, `db.system`, `messaging.destination.name`, `service.name`, …). Never invent ad-hoc keys for standardized concepts — consistency is what makes cross-service correlation possible.

**Reserved attributes for all signals:**
| Attribute | Purpose |
|-----------|---------|
| `service.name` | Logical service name (== the service in the catalog) |
| `service.version` | Deployed version (build sha) |
| `deployment.environment` | `dev` / `qa` / `staging` / `prod` |
| `cloud.provider` | `aws` / `azure` / `gcp` |
| `host.id` / `k8s.pod.name` | Unit of compute |

---

## The Golden Signals & RED / USE

### Golden Signals (Google SRE)
| Signal | Question |
|--------|----------|
| **Latency** | How long does it take to serve a request? |
| **Traffic** | How much demand is on the system? |
| **Errors** | How many requests are failing? |
| **Saturation** | How full is the system? |

### RED (request-oriented — use for services)
- **Rate** — requests per second
- **Errors** — count, and % of requests failing
- **Duration** — distributions, esp. p50/p95/p99

### USE (resource-oriented — use for infrastructure)
- **Utilization** — % of a resource that is busy
- **Saturation** — how much work is queued / waiting
- **Errors** — per-resource error count

**Where:** RED powers SLIs for user-facing services (see [SLI/SLO](./sli-slo.md)); USE powers infrastructure dashboards and capacity alerting.

---

## Correlation: The Single Most Important Property

Logs, metrics, and traces are only truly useful when they can be **joined on a single request**.

- Every log record carries `trace_id` and `span_id`.
- Every span carries `trace_id` + `span_id` and emits its attributes.
- Metrics that originate from request context (RED metrics) are tagged with the same dimensional labels.

**Correlation IDs:**
- `trace_id` is the canonical correlation ID for a single user request flowing through services.
- For non-HTTP async/event workflows, propagate the same `trace_id` through message headers (Kafka message headers, CloudEvents `traceparent` attribute).

**Joining in practice:**
- From a **log** → click the `trace_id` to open the full trace in the APM backend.
- From a **trace** → click a span to see its associated logs.
- From a **metric** → open by label (service, route) and drill into a representative trace or the log stream.

---

## Health & Readiness (probe layer)

Health endpoints are part of observability — they are the signal production/consumption boundary for orchestrators.

- `/health/live` — process is alive (no dependencies) → liveness probe
- `/health/ready` — can serve traffic (checks DB, cache, downstream → readiness probe)
- `/health/startup` — has completed initialization → startup probe (Java launch)

These become inputs to availability SLIs and to the orchestrator (see [microservices](../microservices.md#8-observability-built-in)).

---

## Operational Standard

| Practice | Requirement |
|----------|-------------|
| Instrumentation | OTel SDK + auto-instrumentation in every service, from day one |
| Signals | Logs, metrics, and traces all emitted via OTLP |
| Correlation | `trace_id`/`span_id` present on logs; context propagated across all hops |
| Reserved attributes | `service.name`, `service.version`, `deployment.environment` present on all signals |
| Backend decoupling | No vendor SDKs in application code |
| Health | `/health/live`, `/health/ready`; `/health/startup` where applicable |

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Vendor SDK in app code | Lock-in; migrating backends = code change | Instrument with OTel, export via OTLP |
| Logs-only observability | No causality, no aggregation answers | Add metrics + traces |
| Anonymous/non-structured logs | Unsearchable, uncorrelatable | Structured JSON + `trace_id` |
| Over-instrumentation | Cost + noise | Auto-instrument, add manual spans deliberately |
| Ignoring saturation | Outages hit before metrics show it | Instrument queuing/backpressure (USE) |
| No correlation IDs | Can't stitch a request across services | Propagate `traceparent` everywhere |

---

[← Back to Observability README](./README.md)
