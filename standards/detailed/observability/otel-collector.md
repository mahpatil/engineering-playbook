# OTel Collector

Standards for deploying and configuring the **OpenTelemetry Collector** — the vendor-neutral agent/gateway that receives OTLP telemetry, processes it, and exports it to one or more backends (cloud-native, ELK, Grafana stack, APM, etc.).

---

## Why a Collector

The Collector sits between your instrumented services and your backends so that:

- **Backends are swappable** — exporters target `otlp` / `prometheus` / `loki` / vendor integrations; changing backends is config, not code.
- **Processing is centralized** — sampling, batching, redaction, metric aggregation happen once, not in every app.
- **Resilience** — the Collector buffers and retries when a backend is briefly down.
- **Cloud-native integration** — it consumes k8s/cloud resource attributes and enriches telemetry with platform metadata.

---

## Deployment Topologies

### 1. Agent (DaemonSet / sidecar) — always present

**Per node / per pod.** Collects local host resource attributes, buffers, and forwards to the gateway.

```yaml
# Kubernetes DaemonSet (agent) — one per node
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: otel-agent
  namespace: observability
spec:
  selector:
    matchLabels:
      app: otel-agent
  template:
    metadata:
      labels:
        app: otel-agent
    spec:
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector-contrib:0.100.0
        args: ["--config=/etc/otel/config.yaml"]
        ports:
        - containerPort: 4318   # OTLP HTTP
        - containerPort: 4317   # OTLP gRPC (optional)
        volumeMounts:
        - name: otel-config
          mountPath: /etc/otel
        - name: varlog
          mountPath: /var/log
          readOnly: true
        - name: hostfs
          mountPath: /hostfs
          readOnly: true
      volumes:
      - name: otel-config
        configMap:
          name: otel-agent-config
      - name: varlog
        hostPath:
          path: /var/log
      - name: hostfs
        hostPath:
          path: /
```

### 2. Gateway — for aggregating and fan-out

**Cluster/service-wide.** Receives from agents, applies sampling/redaction, fans out to multiple backends.

---

## Core Collector Concepts

| Concept | Purpose |
|---------|---------|
| **Receiver** | Accepts telemetry (OTLP, Prometheus scrape, filelog, k8s events, …) |
| **Processor** | Transforms data between receive and export (batch, memory limit, filter, sampling, redaction, resource, tail) |
| **Exporter** | Sends data to a backend (OTLP, Prometheus, Loki, Kafka, cloud sinks, vendor exporters) |
| **Pipeline** | Ordered chain: receivers → processors → exporters for a given signal |
| **Service extensions** | Health check, pprof, zpages |

---

## Reference Configuration (Gateway)

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
      grpc:
        endpoint: 0.0.0.0:4317
  prometheus:
    config:
      scrape_configs:
        - job_name: otel-collector
          static_configs:
            - targets: ['localhost:8888']
  # k8s events and cluster metadata
  k8s_cluster:
    auth_type: serviceAccount

processors:
  batch:
    send_batch_size: 1024
    timeout: 5s
  memory_limiter:
    check_interval: 5s
    limit_mib: 512
    spike_limit_mib: 128
  resource:
    attributes:
      - key: deployment.environment
        value: "${ENVIRONMENT}"
        action: upsert
  # (optional) k8s attribute enrichment from resource attributes
  k8sattributes:
    auth_type: serviceAccount
    passthrough: false
  # (optional) tail sampling in gateway for high-volume traces
  tail_sampling:
    decision_wait: 30s
    policies:
      - name: errors-always
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow-traces
        type: latency
        latency:
          threshold_ms: 500
      - name: sample-rest
        type: probabilistic
        probabilistic:
          sampling_percentage: 10

exporters:
  otlp/cloud-native:
    endpoint: https://otlp-aws-endpoint.example:4318   # or GCP/Azure native OTLP
    tls:
      insecure: false
  otlp/apm:
    endpoint: apm-backend:4317
  debug:
    verbosity: basic

service:
  extensions: [health_check, pprof, zpages]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, k8sattributes, batch, tail_sampling]
      exporters: [otlp/cloud-native, otlp/apm]
    metrics:
      receivers: [otlp, prometheus]
      processors: [memory_limiter, k8sattributes, batch]
      exporters: [otlp/cloud-native, otlp/apm]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, k8sattributes, batch]
      exporters: [otlp/cloud-native]
```

---

## Processor Standards (non-negotiable)

| Processor | Why | Setting |
|-----------|-----|---------|
| **batch** | Efficiency — groups signals before export | one per pipeline |
| **memory_limiter** | Avoid OOM / feedback loops | always first in the chain |
| **resource** | Enrich with `deployment.environment`, tenant, team | every pipeline |
| **k8sattributes** | Attach pod/namespace/job labels from k8s metadata | in k8s deployments |
| **filter** (optional) | Drop noisy DB/scrape/health signals | where cost justifies |
| **redaction** (optional) | Strip PII/secrets from attribute values before export | where sensitive data flows |
| **tail_sampling** (optional) | Keep meaningful traces at high volume (errors, slow, then probabilistic) | high-traffic traces in prod |

**Sampling philosophy:**
- **Dev/QA:** 100% sampling (cost is low, fidelity is high).
- **Prod default:** tail sampling that always keeps **errors + slow** traces, then a probabilistic sample of the remainder (e.g., 10%). Keep **metrics aggregated at 100%** — only traces need sampling.

---

## Cloud-Native Integration

The Collector is the natural seam between OTel and cloud-native observability. Two supported patterns:

### Pattern A — Collect locally, export via OTLP to cloud-native APM
All backends below accept **native OTLP**, so the Collector exports `otlp/*` and you get cloud-native APM, metrics, and log correlation with zero vendor SDKs:

| Cloud | Native OTLP backend | Notes |
|-------|--------------------|-------|
| **AWS** | CloudWatch / **ADOT** (AWS Distro for OpenTelemetry) | Managed ADOT Collector; CloudWatch Logs/EMF; X-Ray traces |
| **Azure** | **Azure Monitor / Application Insights** | Native OTLP intake via Application Insights; Log Analytics; App Insights APM |
| **GCP** | **Cloud Monitoring / Cloud Logging / Cloud Trace** | Native OTLP ingestion via OTLP endpoint; Cloud Trace for APM |

### Pattern B — Collect locally, push to open-source stack via exporters
| Signal | Exporter → Store |
|--------|------------------|
| Traces | `otlp/http` → Grafana Tempo, or Jaeger exporter |
| Metrics | `prometheusremotewrite` → Prometheus / Grafana Mimir / VictoriaMetrics |
| Logs | `loki` → Grafana Loki, or `elasticsearch` / `kafka` → ELK |

> The Collector keeps these choices portable: even the *destination* of a signal is just exporter config.

---

## Operational Requirements

| Requirement | Detail |
|-------------|--------|
| Health endpoint | `/health` exposed; wired into k8s liveness/readiness probes |
| Self-monitoring | Collector Scrape job on its own `/metrics` (port 8888) |
| Secrets | Credentials for exporters via env vars / secret mounts, never in committed config |
| Version pinning | Pin `opentelemetry-collector-contrib` image tag; upgrade in test first |
| Resource limits | CPU/memory limits set; `memory_limiter` tuned below container limit |
| Availability | Gateway run with replicas ≥2 in prod; agents are DaemonSets (auto HA) |
| Failure behavior | Collector must never drop in a way that takes down apps; use buffering + backpressure |

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| No memory limiter | OOM loops under burst | Always first processor |
| No batching | Per-signal export = terrible throughput | `batch` in every pipeline |
| Multiple backends wired ad hoc per team | Duplication, inconsistency | One centrally-owned collector config |
| Full sampling in high-volume prod | Cost explosion | Tail sampling (errors+slow+probabilistic) |
| Collector as a SPOF | Loses telemetry if it dies | Agents (DaemonSet) + gateway replicas ≥2 |

---

[← Back to Observability README](./README.md)
