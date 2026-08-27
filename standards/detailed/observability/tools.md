# Observability Tooling & Vendors

A **selection matrix** across the observability surface: instrumentation, collector, metrics, logs, traces/APM, visualization, alerting/on-call, synthetic, RUM, and frontend analytics.

> **Governance:** Prefer **OpenTelemetry + open-source / Grafana stack or the chosen cloud's native OTLP-backed service**. Vendors that only consume proprietary SDKs are disallowed at the instrumentation layer; a proprietary *backend* is acceptable if reached **only via OTLP**.

---

## Instrumentation (unchanged across all backends)

| Layer | Tool |
|-------|------|
| **Unified SDK/API** | **OpenTelemetry (OTel)** — the only sanctioned way to instrument |
| Java agent | `opentelemetry-javaagent` (auto) + Micrometer/OTel bridge |
| Python | `opentelemetry-instrumentation` |
| Node.js/JS | `@opentelemetry/auto-instrumentations-node`; RUM `@opentelemetry/instrumentation` (browser) |
| .NET | `OpenTelemetry.Instrumentation.*` + hosting bundle |
| Go | `go.opentelemetry.io/otel` |
| RUM (browser) | **Grafana Faro**, or cloud-native RUM SDKs (all can emit OTel) |

---

## Collector & Pipeline

| Purpose | Tools |
|---------|-------|
| Collector (agent + gateway) | **OTel Collector**, OTel Collector Contrib; cloud distros: **ADOT** (AWS), Azure Monitor OTLP, GCP OTLP |
| Traffic shaping | batch, memory_limiter, tail_sampling, k8sattributes, redaction processors (in Collector) |
| Kafka transport (optional) | Kafka exporter/topic ingestion for very high volume |

---

## Signal-specific Backends

### Metrics backends
| Category | Tool |
|----------|------|
| Self-hosted open source | **Prometheus**, **Grafana Mimir** / VictoriaMetrics (long-term, HA), Thanos |
| Cloud-native | CloudWatch (Amazon Managed Prometheus / CloudWatch metrics), Azure Monitor / Metrics, GCP Cloud Monitoring |
| SaaS | Datadog, New Relic, Grafana Cloud |

### Logs backends
| Category | Tool |
|----------|------|
| Open source | **Grafana Loki**, **ELK (Elasticsearch + Kibana)**, OpenSearch |
| Cloud-native | CloudWatch Logs, Azure Log Analytics / Sentinel, GCP Cloud Logging |
| SaaS | Datadog Logs, New Relic Logs, Grafana Cloud Logs (Loki) |

### Traces / APM backends
| Category | Tool |
|----------|------|
| Open source | **Grafana Tempo**, **Jaeger**, Zipkin (legacy) |
| Cloud-native | **AWS X-Ray / ADOT**, **Azure Application Insights**, **GCP Cloud Trace** |
| SaaS | Datadog APM, New Relic, Dynatrace, Honeycomb |

---

## Visualization & Dashboards

| Category | Tool |
|----------|------|
| Primary | **Grafana** (dashboards-as-code, OTel-native, unifies metrics+logs+traces+APM) |
| Logs UI | Kibana (with ELK) / Grafana Explore |
| Traces UI | Grafana Tempo diag / Jaeger UI / APM service maps |
| Cloud-native | CloudWatch Dashboards, Azure Workbooks/Dashboards, GCP Monitoring dashboards |

---

## Alerting & On-Call

| Category | Tool |
|----------|------|
| Alert evaluation | **Prometheus/Alertmanager**, Grafana Alerting / Mimir ruler, cloud-native alert policies (CloudWatch Alarm, Azure Monitor alerts, GCP alerting) |
| On-call / incident response | **PagerDuty** (reference), Opsgenie, **Grafana OnCall**, cloud-native equivalents (AWS, Azure Monitor IT, GCP) |
| Chat/escalation | Slack / Teams alert channels, Statuspage (user-facing status) |

---

## Synthetic Monitoring & RUM

| Category | Tool |
|----------|------|
| Synthetic / API / check | Grafana Synthetic Monitoring (**k6**), **Grafana k6** (load/checks), Datadog Synthetics, New Relic Synthetics, AWS CloudWatch Synthetic Canaries, Azure App Insights availability, GCP Synthetic Monitoring |
| RUM / frontend | **Grafana Faro**, Datadog RUM, New Relic Browser, Azure App Insights JS, GCP Web Vitals |
| Load testing (related) | k6, Locust, JMeter |

---

## End-to-End Reference Assembly (recommended default)

```mermaid
flowchart LR
    subgraph Services
      A[App (OTel SDK + agent)]
      B[Frontend (OTel RUM)]
    end
    C[OTel Collector\nagent + gateway]
    D[Grafana stack]
    A --> C
    B --> C
    C --> T[Tempo - traces]
    C --> L[Loki - logs]
    C --> M[Mimir - metrics]
    D --> G[Grafana\n(unified dashboards)]
    M -->|SLO burn| R[Alerting]
    R --> P[PagerDuty]
```

**Default open-source stack:** OTel → OTel Collector → **Grafana + Tempo + Loki + Mimir** → Grafana Alerting → PagerDuty, with **Faro** for RUM and **k6 Synthetic Monitoring** for active checks.

**Cloud-native default:** OTel → ADOT / native OTLP → **cloud-native APM + metrics + logs** (X-Ray, CloudWatch, Azure App Insights, GCP Trace) → cloud alerting → PagerDuty, everything reached via OTLP so it stays portable.

**ELK default:** OTel → Collector (`elasticsearch`/`kafka` exporters) → **Elasticsearch + Kibana** for logs/SIEM, with Tempo or Jaeger for traces; Grafana optional for unified dashboards.

---

## Selection Decision Rules

| Situation | Prefer |
|-----------|--------|
| Clear cloud commitment, want zero self-hosting | Cloud-native OTLP backends |
| Open-source-first, budget-sensitive, want a single UI | Grafana stack (Tempo/Loki/Mimir) |
| Deep log search + existing security/SIEM needs | ELK (Elasticsearch + Kibana) |
| Managed SaaS, max features per dollar | Datadog / New Relic / Grafana Cloud (all OTel-native) |
| High-cardinality tracing & correlation at scale | Honeycomb or Tempo + aggressive labeling |
| Heavy frontend/UX focus | Grafana Faro + k6 Synthetic |

**Hard requirements for any chosen backend:**
- Native **OTLP intake** (no proprietary agent)
- Log, trace, and metric **correlation** (shared `trace_id`)
- **Dashboards as code**
- Supported **API/SDK** for alert config as code
- Transparent **pricing** that matches volume (watch cardinality + retention)

---

## Compatibility: OTel ↔ Backends Quick Map

| Backend | Traces | Metrics | Logs | Native OTLP |
|---------|:------:|:-------:|:----:|:-----------:|
| Grafana Tempo | ✅ | — | — | ✅ |
| Grafana Loki | — | — | ✅ | ✅ (logproto issue) |
| Grafana Mimir / Prometheus | — | ✅ | — | ✅ (OTLP traits) |
| Jaeger | ✅ | — | — | ✅ |
| Elasticsearch / OpenSearch | (with APM) | — | ✅ | via exporter |
| CloudWatch / ADOT (AWS) | ✅ X-Ray | ✅ | ✅ | ✅ |
| Azure Monitor / App Insights | ✅ | ✅ | ✅ | ✅ |
| GCP Monitoring / Trace / Logging | ✅ | ✅ | ✅ | ✅ |
| Datadog | ✅ | ✅ | ✅ | ✅ |
| New Relic | ✅ | ✅ | ✅ | ✅ |
| Dynatrace | ✅ | ✅ | ✅ | ✅ |
| Honeycomb | ✅ | — | ✅ (event actors) | ✅ |

---

## Cost & Capacity Guardrails

| Item | Guardrail |
|------|-----------|
| Trace sampling | Tail-sample prod (keep errors+slow, then probabilistic) |
| Metric cardinality | Bounded labels; prefer aggregation of high-cardinality |
| Log volume | Structured summaries; DEBUG off in prod; hot→cold retention |
| Retention | Hot 7–30 days; cold archive for compliance only |
| RUM | Sample + aggregate by route/device/browser; don't ship full payloads |
| Alert budget | Track alert volume per incident; cut noise |

---

[← Back to Observability README](./README.md)
