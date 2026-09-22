# Metrics & Dashboards

Standards for **metrics semantics**, the **metrics pipeline**, and **dashboards-as-code** (Grafana). Metrics answer "is something happening, and how much?" at aggregate scale.

---

## Metric Model

| Type | Nature | Use For | OTel name |
|------|--------|---------|-----------|
| **Counter** | Monotonic, ever-increasing | Requests, errors, bytes | `Counter` |
| **Gauge** | Point-in-time value, up/down | Queue depth, connections, temp | `Gauge` (observable) |
| **Histogram** | Distribution of values → percentiles | Latency, request size | `Histogram` |

**Standard metrics carry these labels (dimensions):** `service.name`, `service.version`, `deployment.environment`, `http.route`, `http.response.status_code`, `db.system`, `messaging.destination.name`, plus business dimensions (`status`, `tenant`, `region`, …).

> Keep cardinality bounded: finite, well-defined label values. Unbounded labels (e.g., raw `requestId`) fragment the TSDB and explode cost.

---

## The Metrics We Require

### RED — for every service (request-oriented)
| | Metric | Source |
|-|--------|--------|
| **Rate** | `http.server.request.duration` count (requests/s) | auto-instrumentation |
| **Errors** | count of 5xx + error ratio | auto-instrumentation |
| **Duration** | latency histogram → p50/p95/p99 | auto-instrumentation |

### USE — for infrastructure/resources
| | Metric | Example |
|-|--------|---------|
| **Utilization** | % of resource busy | CPU, memory, connection pool usage |
| **Saturation** | queued / waiting | queue depth, thread pool saturation, disk I/O wait |
| **Errors** | resource error count | I/O errors, dropped packets |

### Business metrics (manual, domain meaning)
```yaml
orders.created.total{status="success|error"}
order.processing.duration{status}
payment.attempts.total{result="success|failed|timeout"}
cart.abandonment.rate
cache.hit.ratio
```

### JVM / runtime (auto)
`jvm.memory.used`, `jvm.gc.duration`, `jvm.threads.live` (Java), plus language equivalents (Go/Python/Node/.NET).

---

## Metrics Pipeline

```text
Apps ──OTLP/metrics──▶ OTel Collector (batch, filter, resource) ──▶ backend
                                                                      │
                            Prometheus/Mimir/VictoriaMetrics │        │
                            CloudWatch/Stackdriver/Azure Monitor       ▼
                                                          Grafana (query + visualize)
```

- Apps **push** via OTLP to the Collector (preferred — pull-free, works for short-lived tasks).
- The Collector may **scrape** infrastructure (Prometheus receiver) and aggregate.
- **Do not** expose metrics only on a pull endpoint (`/metrics`) in isolation — push via OTLP for unified handling, keep a scrape endpoint only when a pull-based stack mandates it.

---

## Dashboards as Code

Dashboards are **versioned artifacts**, reviewed and deployed like code — never hand-clicked into a board that only one person can reproduce.

### Grafana provisioning (file-based)
```yaml
# grafana/provisioning/dashboards/dashboards.yaml
apiVersion: 1
providers:
  - name: default
    folder: Services
    type: file
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

Keep dashboard **JSON in git** (e.g., `grafana/dashboards/<service>.json`), and where supported generate from `grafonnet` / `jsonnet`.

---

## Standard Dashboard Set

1. **Service Overview (per service)** — RED
   - Request rate (by route/status)
   - Error rate
   - Latency percentiles (p50/p95/p99)
   - Availability (from SLI)
2. **Reliability / SLO** — see [SLI/SLO](./sli-slo.md)
   - Error budget remaining, burn rate
3. **Runtime** — JVM / pod
   - Heap, GC pauses, threads; CPU/mem (USE)
4. **Dependencies**
   - Downstream service latency/errors, DB connection pool, message queue depth
5. **Business Metrics**
   - Orders/min, payment success rate, conversion funnel
6. **Infrastructure (cluster-level)**
   - Node CPU/mem, pod restarts, network I/O, saturation

**Dashboard criteria for every board:**
- Tells a story in ≤10 tiles / ~5 min of reading.
- Row titles answer a question ("Is the service healthy? Where is latency?").
- Titles link to the owning runbook.
- SLO boards show the **agreed target** + error budget, not just raw data.
- Dashboards are annotated on deploys (deploy events overlaid) so you can correlate changes with metric movements.

---

## Alerting vs. Dashboards

- **Dashboards** are for *human* reading and post-incident analysis.
- **Alerts** are for *machine* paging — driven by SLO burn rate, not by staring at a board (see [Alerting & On-Call](./alerting-oncall.md)).
- Keep the two coupled: an alert should point to the exact dashboard/runbook that explains it.

---

## Operational Standards

| Practice | Requirement |
|----------|-------------|
| Semantic conventions | OTel metric naming/units (`*_total`, `*_duration`, unit `s`/ms) |
| RED + USE | Present per service and per resource |
| Cardinality | Bounded label values; no `requestId`-style labels |
| Aggregation | 100% — never sample metrics |
| Dashboards-as-code | JSON in git, provisioned via Grafana |
| Deploy annotations | Overlaid on dashboards |
| Units | Histograms in seconds where OTel convention requires |

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Averages only | Hides p99 pain | Histograms + percentiles |
| High-cardinality labels | TSDB bloat, cost | Bound dimensions |
| Dashboards built by hand only | Non-reproducible, drift | Dashboards-as-code |
| Alerting on raw graphs | Noise, misses SLO | Alert on burn rate (see alerting) |
| Metrics app-side only, no infra | Blind to saturation | Add USE metrics |

---

[← Back to Observability README](./README.md)
