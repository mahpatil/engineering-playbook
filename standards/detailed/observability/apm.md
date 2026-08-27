# APM & Distributed Tracing

Standards for **Application Performance Monitoring (APM)** and **distributed tracing** — the ability to follow a single request end-to-end across every service, queue, and dependency, and to answer "where is the time and the failure going?"

---

## What APM Is

APM unifies **traces** (request-level causality/path) with **metrics** (aggregate performance) and the service map derived from them. In an OTel-first world, APM is a *backend* that consumes OTLP and renders:

- distributed traces + waterfall / flame views
- service dependency maps
- per-service RED metrics (rate / errors / duration)
- trace → log correlation

It is **not** a separate instrumentation SDK — it is what the OTel Collector exports to (see [OTel Collector](./otel-collector.md)).

---

## Trace Model (OTel)

| Term | Meaning |
|------|---------|
| **Trace** | The full lifecycle of one logical request, identified by `trace_id` |
| **Span** | A single logical unit of work within a trace, identified by `span_id`, with a parent link |
| **Root span** | First span in a trace (no parent); usually the inbound request handler |
| **Span kind** | `SERVER` (receiving), `CLIENT` (outbound call), `PRODUCER`/`CONSUMER` (messaging), `INTERNAL` |
| **Event** | Timestamped annotation within a span (e.g., "cache miss", "retry") |
| **Status** | `UNSET`, `OK`, or `ERROR` + human message |
| **Link** | Reference to another span/trace (fan-in, batch, async) without full nesting |

**Span attributes** follow OTel semantic conventions: HTTP method/status, DB system/statement, messaging destination, RPC system, etc.

---

## Distributed Trace: Reference Example

```yaml
# Logical trace for GET /api/v1/orders/123
trace_id: 4bf92f3577b34da6a3ce929d0e0e4736
├── span A  [SERVER]  GET /orders/{id}            order-api       404ms
│   ├── span B  [CLIENT]   auth check              → auth-service    12ms
│   ├── span C  [CLIENT]   POST order.events       → (Kafka) producer 3ms
│   └── span D  [CLIENT]   SELECT orders           → postgres       340ms
└── (downstream consumer)
    └── span E  [CONSUMER] process order.events    order-worker    8ms
```

**What it tells you:** the request spent ~340ms of its 404ms in the database; the auth call is fast; the event publish is asynchronous and cheap. This tells you exactly where latency is concentrated and lets you click any span to read that service's logs.

---

## Context Propagation (the critical mechanism)

Spans become a distributed trace only if **context crosses process boundaries**. This is automatic for HTTP/gRPC via the W3C `traceparent` header and for messaging via message headers, but must be *verified*, not assumed.

### Must propagate context across:
| Boundary | Mechanism |
|----------|-----------|
| HTTP / HTTPS | `traceparent` + `tracestate` headers (W3C) |
| gRPC | `traceparent` through gRPC metadata |
| Kafka / queues | `traceparent` in message headers (producer injection + consumer extraction) |
| CloudEvents | `traceparent` extension attribute |
| Scheduled jobs / batch spawn | Parent span passed into child `Context` (manual, language-dependent) |

### Async propagation (Java example)
```java
// Preserve context so async work lands under the parent trace
Context ctx = Context.current();
executor.submit(() -> {
    try (Scope scope = ctx.makeCurrent()) {
        // this work is part of the same trace
    }
});
```

### Kafka producer example
```java
@Bean
public ProducerFactory<String,Object> producerFactory() {
    return new DefaultKafkaProducerFactory<>(configs,
        new StringSerializer(), new JsonSerializer<>(),
        true);   // instrumentation propagates trace data into headers
}
```

---

## Trace → Metrics (the service map & RED)

Beyond the raw trace, the collector/backend derives aggregate metrics:
- **Span call count** per (service, operation, status_code) → request/error rate
- **Span duration histogram** → latency percentiles
- These feed the **service map** and RED dashboards.

Result: you can toggle between "one trace" and "system-wide aggregates" without separate instrumentation.

---

## Sampling Strategy

Sampling trades fidelity for cost/volume. Standard (see [OTel Collector](./otel-collector.md#processor-standards)):

| Environment | Traces | Metrics |
|-------------|--------|---------|
| Dev / QA | 100% (head sampling; cheap) | 100% |
| Prod | Tail sampling: keep errors + slow (e.g., >500ms), then probabilistic (e.g., 10%) of the rest | 100% aggregated |

**Principles:**
- **Never sample metrics** — they are the cheap-to-keep aggregates.
- **Always keep error and slow traces** — they are the highest-value signals.
- Tail sample at the **gateway**, so decisions are consistent fleet-wide.

---

## APM Backend Requirements (what to demand of your APM)

| Requirement | Why |
|-------------|-----|
| OTLP intake (native) | No vendor SDK; portable |
| Trace → log correlation | Click span → read logs; click log → open trace |
| Service map | See dependencies, spot hidden coupling |
| RED metrics per service/route | Standard performance triage |
| Error tracking with stack traces | Fast root-cause on exceptions |
| SLO/burn-rate integration | Tie tracing + metrics to error budgets (see [SLI/SLO](./sli-slo.md)) |
| Histogram-based latency | p50/p95/p99, not averages |

---

## APM Tool Options

> Full matrix in [Tooling & Vendors](./tools.md). Headline options:

| Category | Tools |
|----------|-------|
| Open-source / Grafana stack | **Grafana Tempo** (trace store), Jaeger (trace UI), Grafana (visualization) |
| Cloud-native (no vendor SDK, via OTLP) | **AWS X-Ray / ADOT**, **Azure Application Insights / Monitor**, **GCP Cloud Trace** |
| Commercial SaaS | Datadog APM, New Relic, Dynatrace, Honeycomb (high-cardinality, trace-first) |

---

## Operational Standards

| Practice | Requirement |
|----------|-------------|
| Inbound spans | Every request/command handler has a root span (SERVER) |
| Outbound spans | Every downstream call, DB query, and publish is a child span (CLIENT/PRODUCER) |
| Status set | Error status + recorded exception on every failed operation |
| Sampling | Tail sampling in prod (errors+slow kept); metrics unsampled |
| Context | `traceparent` verified across every HTTP/gRPC/messaging boundary |
| Naming | Span names from OTel semantic conventions; `service.name` consistent |

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Broken propagation | Trace dies at first hop | Verify `traceparent` across HTTP/queues |
| Sampling errors/large traces | Lose the exact signals you need | Keep errors+slow in tail sampling |
| Averages only | Hides the 99th percentile | Use histograms (p95/p99) |
| Vendor SDK for tracing | Lock-in | OTel SDK → OTLP → backend |
| Span explosion | Storage/sampling cost, noise | Sampler + semantic-convention discipline |

---

[← Back to Observability README](./README.md)
