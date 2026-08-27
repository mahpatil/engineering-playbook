# Centralized Logging

Standards for **structured logging** and the **centralized log pipeline** — how application logs are produced, transported, stored, searched, and correlated with traces. Covers the ELK stack, Grafana Loki, and cloud-native log stores.

---

## Principles

1. **Structured JSON by default.** Logs are machine-readable records, not free text.
2. **Correlation built in.** Every log carries `trace_id` / `span_id`.
3. **Logs are low-fidelity diagnostics.** The *why* behind a metric/trace; not the only signal.
4. **Ship everything to one pipeline.** No team-owned log silos.
5. **Enough context, never secrets.** Add request/service context; redact PII and credentials.

---

## Structured Logging Format

All logs use **structured JSON** with a consistent schema:

| Field | Description | Example |
|-------|-------------|---------|
| `@timestamp` | ISO 8601 UTC | `2026-08-27T10:30:00.000Z` |
| `level` | `DEBUG`/`INFO`/`WARN`/`ERROR` | `INFO` |
| `service.name` | Logical service | `order-service` |
| `service.version` | Release/build | `1.4.2` |
| `trace_id` | Distributed trace ID | `4bf92f3577b34da6` |
| `span_id` | Current span | `6326310517e59f63` |
| `message` | Human-readable text | `Order created` |
| `logger` | Class/component | `com.example.OrderService` |
| `*` (context) | Domain-specific fields | `orderId`, `customerId`, `status` |

### Level semantics
| Level | Use For |
|-------|---------|
| `ERROR` | Failures needing attention; map to error-rate metrics |
| `WARN` | Unexpected but handled (retry, degraded path, circuit open) |
| `INFO` | Business events, lifecycle (start/stop), request/response summaries |
| `DEBUG` | Development; off in prod unless temporarily enabled |

**Log volume guidance:** log **business events and lifecycle**, not per-request debug noise in prod. When you log per request, log a summary, not the full payload.

---

## Java / Logback Example

```xml
<!-- logback-spring.xml -->
<configuration>
  <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <includeMdcKeyName>traceId</includeMdcKeyName>
      <includeMdcKeyName>spanId</includeMdcKeyName>
      <includeMdcKeyName>service.name</includeMdcKeyName>
    </encoder>
  </appender>
  <root level="INFO">
    <appender-ref ref="JSON"/>
  </root>
</configuration>
```

```java
@Service
public class OrderProcessor {
    private static final Logger log = LoggerFactory.getLogger(OrderProcessor.class);

    public void process(Order order) {
        log.atInfo()
            .addKeyValue("orderId", order.id().toString())
            .addKeyValue("customerId", order.customerId().toString())
            .addKeyValue("amount", order.total())
            .addKeyValue("event", "order.processing.started")
            .log("Processing order");
    }
}
```

> The OTel Java agent + Micrometer tracing bridge **injects `traceId`/`spanId` into MDC automatically**, so structured loggers pick them up without manual work.

---

## Correlation with Traces

- Every log record carries `trace_id` / `span_id`.
- **Log → trace:** click the `trace_id` in the log viewer to open the full distributed trace in the APM backend.
- Ensure the log forwarder preserves these fields (don't drop the OTel keys during transport).

---

## The Centralized Log Pipeline

```text
Apps ─┬─> OTLP logs ──────────────┐
      └─> filelog / stdout ───────┴─> OTel Collector (agent+gateway) ─> Log store (search/analytics)
                                                                                 │
                                        Grafana Loki | ELK/Elasticsearch |       ▼
                                        CloudWatch | Azure Log Analytics |   Kibana / Grafana
                                        GCP Cloud Logging                     (visualization)
```

Two ingestion paths (often both):

| Path | Mechanism | Use for |
|------|-----------|---------|
| **OTLP logs** | OTel SDK log appender → Collector | Structured, correlated app logs |
| **filelog / stdout scraping** | Collector `filelog` receiver reads container stdout / journald / files | Infra logs, container logs, legacy apps |

---

## Log Store Backends

| Store | Strengths | When to choose |
|-------|-----------|----------------|
| **Grafana Loki** | Cheap, indexes labels not contents, native to Grafana, pull via OTLP/logproto | Grafana-centric orgs; high volume; budget-conscious |
| **ELK (Elasticsearch + Kibana)** | Full-text search, aggregations, mature SIEM/security ecosystem | Deep log analytics, security/compliance search, existing ES ops |
| **Cloud-native (CloudWatch Logs, Azure Log Analytics / Sentinel, GCP Cloud Logging)** | Zero self-hosting, native alerting + audit archives, IAM | Teams already on the cloud; audit/compliance needs |
| **Kafka → clickhouse/elasticsearch (custom)** | Very high throughput, replay | Extreme volumes / custom analytics |

**Search/index policy:** index hot data for interactive search (e.g., 7–30 days); archive the rest to cold/object storage for compliance and replay.

---

## Security, Privacy & Compliance

| Requirement | Detail |
|-------------|--------|
| Redaction | Strip PII and secrets in the Collector (`redaction` processor) or at the app before log emission |
| No secrets in logs | Passwords, tokens, keys never logged — anywhere |
| Access control | Log store behind SSO/RBAC; team/project scoping |
| Retention | Defined by compliance + cost; audit logs preserved per regulatory requirement |
| Encryption | TLS in transit; encrypted at rest in the store |
| Audit logs | Platform/CI/CD audit events flow to the same pipeline with longer retention |

---

## Operational Standards

| Practice | Requirement |
|----------|-------------|
| Format | Structured JSON, schema as defined |
| Correlation | `trace_id`/`span_id` on every log |
| Centralization | All logs to one pipeline; no silos |
| Volume control | Log business events; keep prod DEBUG off |
| Retention | Hot: 7–30 days; cold archive for compliance |
| Alerting from logs | Secondary to metrics; use log-derived alerts sparingly |

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Unstructured (free text) logs | Unsearchable, uncorrelatable | Structured JSON |
| Logging as the only signal | No aggregates/causality at scale | Add metrics + traces |
| Secret in logs | Breach | Redact; never log tokens |
| `DEBUG` in prod | Cost + noise | `INFO`+ default; targeted debug on demand |
| Per-request full payloads | Storage explosion | Log summaries + business events |
| Team log silos | Can't see end-to-end | One centralized pipeline |

---

[← Back to Observability README](./README.md)
