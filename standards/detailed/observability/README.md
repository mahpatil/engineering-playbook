# Observability Standards

Standards for **logs, metrics, traces, and alerts** built on **OpenTelemetry (OTel)** as the unifying instrumentation layer, decoupled from any single vendor so the organization can adopt cloud-native (native observability, Prometheus, Grafana, Loki) or commercial (ELK, Datadog, New Relic) backends as needs evolve.

---

## Documents

| Standard | What It Covers |
|----------|---------------|
| [Core Observability](./core-observability.md) | The three pillars, OTel SDK/auto-instrumentation, signal correlation, the golden signals, RED/USE methods |
| [OTel Collector](./otel-collector.md) | Collector architecture, pipelines, processors, exporters, sampling, cloud-native integration (k8s, managed cloud backends) |
| [APM & Tracing](./apm.md) | Distributed tracing deep dive, span/trace semantics, context propagation, trace → metrics export, APM tooling |
| [Centralized Logging](./logs.md) | Structured logging, logging pipelines, ELK / Loki / cloud-native stores, log → trace correlation |
| [Metrics & Dashboards](./metrics-dashboards.md) | Metric types, required RED/USE metrics, Prometheus exposition, Grafana dashboards-as-code |
| [SLI / SLO](./sli-slo.md) | SLI/SLO definitions, error budgets, margin, SLO-driven alerting and burn-rate policy |
| [Alerting & On-Call](./alerting-oncall.md) | Alerting philosophy, severity, routing, escalation, PagerDuty integration, runbooks, on-call rotation |
| [Synthetic & RUM](./synthetic-rum.md) | Synthetic monitoring, browser/API checks, Real User Monitoring (RUM), frontend/UX analytics |
| [Tooling & Vendors](./tools.md) | Full tool matrix and selection guidance across open-source, cloud-native, and commercial options |

---

## Where to Start

**New to observability?** Start with [Core Observability](./core-observability.md) — it explains the three pillars, the golden signals, and why OTel is the foundation.

**Instrumenting a service?** Read [Core Observability](./core-observability.md) (SDK/auto-instrumentation) then [OTel Collector](./otel-collector.md) (where signals go).

**Defining reliability targets?** Go to [SLI / SLO](./sli-slo.md), then [Alerting & On-Call](./alerting-oncall.md) to wire those targets to paging.

**Doing a frontend/UX rollout?** Go to [Synthetic & RUM](./synthetic-rum.md).

**Choosing a backend?** Go to [Tooling & Vendors](./tools.md) and [OTel Collector](./otel-collector.md).

---

## Guiding Principles

1. **OpenTelemetry first.** Instrument once with OTel; never couple application code to a specific backend (Prometheus, ELK, Datadog, etc.).
2. **Correlate everything.** Logs, traces, and metrics are joined by `trace_id`, `span_id`, `service.name`, and `environment`.
3. **Observe at every layer.** Application, infrastructure, network, data, and UX are all first-class surfaces.
4. **Reliability is engineering, not heroics.** SLIs → SLOs → error budgets → alerting, so engineers are paged on user impact, not on noise.
5. **Everything as code.** Dashboards, alerts, SLOs, and synthetic checks are versioned artifact alongside the service.
6. **Vendor-portable.** OTel decouples instrumentation from storage/analysis, so switching backends is zero code change.

---

## Related Standards

- [Microservices](../microservices.md) — observability built into every service (health checks, RED metrics, correlation IDs)
- [API Design](../api-design.md) — error handling and status semantics that feed SLIs
- [CI/CD Pipeline](../cicd-pipeline.md) — observability deployed as part of the service
- [Integration / Event-Driven](../integration/event-driven-architecture.md) — trace and log context across async/messaging boundaries
- [Overall: Metrics & Success Indicators](../../overall/metrics.md) — engineering flow and DORA metrics
