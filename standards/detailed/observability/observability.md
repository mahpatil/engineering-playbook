# Observability Standards

Detailed standards for **logs, metrics, traces, and alerts** built on **OpenTelemetry (OTel)** as the unifying instrumentation layer, decoupled from any single vendor so the organization can adopt cloud-native (native observability, Prometheus, Grafana, Loki) or commercial (ELK, Datadog, New Relic) backends as needs evolve.


> 💡 Observability as an afterthought, makes the system opaque and failures invisible until they become outages.

---


## Key Business Drivers


| Driver | Outcome         |
|--------|-----------------|
|**Reliability & SLA Assurance**| Health probes and RED-method metrics provide the evidence needed to measure and defend uptime commitments |
|**Proactive Detection**        | Metrics based alerts on error rates, capacity issues and p95/p99 latency surface degradation before it becomes an outage |
|**Data-Driven Decisions**      |Request-rate and throughput metrics inform scaling, capacity planning, and prioritization |
|**Faster Incident Resolution** | Structured logs and correlation IDs let teams trace a failure across services quickly, cutting **mean-time-to-recovery (MTTR)** |
|**Root-Cause Visibility**      | Distributed traces follow a request across every service boundary, pinpointing where latency or errors originate |
|**Operational Independence**   | Per-service dashboards and alerts let autonomous teams operate their own services without central gatekeeping |
|**Reduced Debugging Cost**     | Instrumentation from day one avoids costly retrofitting and shortens the time engineers spend diagnosing issues |


---

## Guiding Principles

1. **Standards (OpenTelemetry) first.** Instrument once with OTel; never couple application code to a specific backend (Prometheus, ELK, Datadog, etc.).
2. **Correlate everything.** Logs, traces, and metrics are joined by `trace_id`, `span_id`, `service.name`, and `environment`.
3. **Observe at every layer.** Front-end (UX), Application, infrastructure, network, data and integrations are all first-class surfaces.
4. **Reliability is engineering, not heroics.** SLIs → SLOs → error budgets → alerting, so engineers are paged on user impact, not on noise.
5. **Everything as code.** Dashboards, alerts, SLOs, and synthetic checks are versioned artifact alongside the service.
6. **Vendor-portable.** OTel decouples instrumentation from storage/analysis, so switching backends is zero code change.

---

## Standards Map

| Standard | What It Covers |
|----------|---------------|
| [Core Observability](./core-observability.md) | The three pillars, OTel SDK/auto-instrumentation, signal correlation, the golden signals, RED/USE methods |
| [Centralized Logging](./logs.md) | Structured logging, logging pipelines, ELK / Loki / cloud-native stores, log → trace correlation |
| [OTel Collector](./otel-collector.md) | Collector architecture, pipelines, processors, exporters, sampling, cloud-native integration (k8s, managed cloud backends) |
| [APM & Tracing](./apm.md) | Distributed tracing deep dive, span/trace semantics, context propagation, trace → metrics export, APM tooling |
| [Metrics & Dashboards](./metrics-dashboards.md) | Metric types, required RED/USE metrics, Prometheus exposition, Grafana dashboards-as-code |
| [SLI / SLO](./sli-slo.md) | SLI/SLO definitions, error budgets, margin, SLO-driven alerting and burn-rate policy |
| [Alerting & On-Call](./alerting-oncall.md) | Alerting philosophy, severity, routing, escalation, PagerDuty integration, runbooks, on-call rotation |
| [Synthetic & RUM](./synthetic-rum.md) | Synthetic monitoring, browser/API checks, Real User Monitoring (RUM), frontend/UX analytics |
| [Tooling & Vendors](./tools.md) | Full tool matrix and selection guidance across open-source, cloud-native, and commercial options |

---

## Where to Start

- **New to observability?** Start with [Core Observability](./core-observability.md) — it explains the three pillars, the golden signals, and why OTel is the foundation.
- **Instrumenting a service?** Read [Core Observability](./core-observability.md) (SDK/auto-instrumentation) then [OTel Collector](./otel-collector.md) (where signals go).
- **Defining reliability targets?** Go to [SLI / SLO](./sli-slo.md), then [Alerting & On-Call](./alerting-oncall.md) to wire those targets to paging.
- **Doing a frontend/UX rollout?** Go to [Synthetic & RUM](./synthetic-rum.md).
- **Choosing a backend?** Go to [Tooling & Vendors](./tools.md) and [OTel Collector](./otel-collector.md).

---

## Related Standards

- [Microservices](../microservices.md) — observability built into every service (health checks, RED metrics, correlation IDs)
- [API Design](../api-design.md) — error handling and status semantics that feed SLIs
- [CI/CD Pipeline](../cicd-pipeline.md) — observability deployed as part of the service
- [Integration / Event-Driven](../integration/event-driven-architecture.md) — trace and log context across async/messaging boundaries
- [Overall: Metrics & Success Indicators](../../overall/metrics.md) — engineering flow and DORA metrics
