# SLI / SLO

Standards for defining **Service Level Indicators (SLIs)** and **Service Level Objectives (SLOs)**, computing **error budgets**, and turning those budgets into **burn-rate alerting** so engineers are paged on real user impact — not on noise.

---

## Terms

| Term | Definition |
|------|-----------|
| **SLI** | A **measure** of a user-facing behavior (e.g., "fraction of valid requests served in < 500ms"). |
| **SLO** | The **target** for that SLI over a period (e.g., "99.5% of requests < 500ms over rolling 30 days"). |
| **Error budget** | `1 − SLO` — how much unreliability is *allowed* per period before users are hurt. |
| **Burn rate** | How fast the error budget is being consumed relative to the SLO. |

> **SLA ≠ SLO.** SLA is a contractual/legal commitment (often financial). SLO is an internal engineering target. Set internal SLOs **stricter than** (> or =) legal SLAs so you have margin.

---

## Principles

1. **SLIs come from user-visible behavior**, not internal implementation.
2. **Start with availability = > create baseline, then add latency.**
3. **Keep SLOs simple** — a handful per service, not a catalog.
4. **SLOs are honesty and cost**, not a number to game — the budget is real and usable.
5. **Alert on burn rate**, not on raw threshold breaches.

---

## Choosing an SLI

An SLI is a **ratio of good events to total events** over a window:

```
SLI = good_events / total_events
```

### The two canonical SLIs

**1. Availability (request success)**
```promql
sum(rate(http_server_request_duration_seconds_count{status!~"5.."}[5m]))
-----------------------------------------------------------
sum(rate(http_server_request_duration_seconds_count[5m]))
```
> Note: this uses *non-5xx* as "good". Optionally exclude 4xx that are truly client faults — but decide this once per service and document it; lazy 4xx-exclusion can hide real problems.

**2. Latency (percentile) — e.g., p95 < 500ms**
```promql
histogram_quantile(0.95,
  sum(rate(http_server_request_duration_seconds_bucket[5m])) by (le)
) < 0.5
```

### Advanced SLIs (use where relevant)
- **Durability / freshness** for data pipelines: fraction of events processed within X latency (queue age).
- **Synthetic availability** — see [Synthetic & RUM](./synthetic-rum.md).
- **Saturation** — guardrails, not usually an SLO.

---

## Setting SLOs

| Service tier | Typical SLO |
|--------------|-------------|
| Tier 0 (customer-critical, revenue) | 99.95–99.99% availability; p95 < 100ms |
| Tier 1 (core) | 99.9%; p95 < 500ms |
| Tier 2 (supporting) | 99.5%; p95 < 1s |
| Internal/tooling | 99.0% |

**Rule:** SLOs are per (service, user-facing path or metric). Set them where they matter; don't force SLOs onto background jobs that have no user-facing latency contract (use freshness/durability SLIs instead).

**Example SLO table:**
| Service | Availability | Latency | Error rate |
|---------|--------------|---------|------------|
| API Gateway | 99.9% | p99 < 150ms | < 0.1% |
| Order Service | 99.5% | p95 < 500ms | < 1% |
| Catalog Service | 99.5% | p95 < 300ms | < 1% |

---

## Error Budget Math

```
Error budget = 1 − SLO
Monthly budget (minutes) = (1 − SLO) × minutes in month

Example: 99.5% availability, 43,200 min/month
Error budget = 0.5% = 216 minutes of permitted downtime per month
```

**If the error budget is exhausted → take deliberate action:** stop risky releases, prioritize reliability work. The budget is a *decision-making tool*, not a punishment.

---

## Burn-Rate Alerting (the standard)

**Never page on "SLI crossed the SLO line."** By the time the SLO is breached, you may already be out of budget. Instead, alert on **burn rate** — how fast the error budget is being spent.

Set multi-window multi-burn-rate rules (Google SRE):

| Burn rate | Detection window | Meaning / action |
|-----------|------------------|------------------|
| **14.4×** | 1 hour (≥14.4% budget) | Critical — page on-call now (≤15 min) |
| **6×** | 6 hours (≥3% budget) | Warning — alert team |
| **1×** | 30 days (≥0.1% at the close of window) | Long-term compliance — ticket |

`burn_rate = error_budget_consumed / fraction_of_period_elapsed`

**Grafana / Prometheus burn-rate alert example (multi-window):**
```yaml
groups:
  - name: slo
    rules:
      - alert: SLOHighBurnRate
        expr: |
          sum(rate(http_server_request_duration_seconds_count{status!~"5.."}[15m]))
          / sum(rate(http_server_request_duration_seconds_count[15m]))
          < 0.994
        for: 1h
        labels: { severity: critical }
        annotations:
          summary: "Error budget burning at 14.4x+ for order-service"
          runbook: "https://runbooks.example.com/slo-burn"
```

Pair the burn-rate signal with the **error-budget graph** on the SLO dashboard so on-call sees the context instantly.

---

## SLO Management / Ownership

| Concern | Standard |
|---------|----------|
| Definition | SLOs written as code (config/SLI file) in the service repo |
| Review | Reviewed quarterly; tightened, never silently loosened during a crisis |
| Ownership | Each SLO has a named owning team on-call |
| Visibility | SLO/error-budget dashboard per service, linked to runbook |
| Blameless | Budgets spent → retrospective + reliability work, not blame |

---

## Operational Standards

| Practice | Requirement |
|----------|-------------|
| Availability SLI | Every user-facing service |
| Latency SLI | p95/p99 tied to user journey tolerance |
| SLO as code | Versioned in service repo |
| Alerting | Burn-rate (14.4×/6×/1×), not raw breach |
| Error budget | = 1 − SLO; dashboarded + driver of release decisions |
| Margin | Internal SLO ≥ legal/business SLA |

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| No SLOs | No definition of "good", paging chaos | Define SLI/SLO on user-visible behavior |
| Alerting on SLO breach | Budget already gone when you page | Burn-rate alerting |
| Gaming 4xx exclusion | Hides real failures | Decide exclusions once, document, review |
| SLO >= SLA by accident | Legal breach before internal alarm | Internal SLO strictly better than SLA |
| "100%" SLO | Meaningless, impossible, will be violated | Realistic target (99.0–99.99%) |
| Forgotten budget | Unchecked reliability debt | Error budget on dashboard + gating |

---

[← Back to Observability README](./README.md)
