# Data Integration Patterns

Patterns for synchronizing, streaming, and governing data across services, domains, and analytical systems.

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Real-Time Decisioning** | Downstream systems and analytics act on fresh data instead of stale nightly batches |
| **Decoupled Systems** | Producers and consumers evolve independently without breaking each other |
| **Single Source of Truth** | Every consumer reads the same authoritative version of a data entity |
| **Scalable Analytics** | Data lakes/warehouses stay current without overloading source systems |
| **Domain Autonomy** | Teams own and expose their data as a product, without ad-hoc point-to-point pipelines |
| **Auditability & Compliance** | Data lineage, schema history, and access are tracked for regulated workloads |
| **Resilience** | Integration pipelines survive partial failures without data loss or duplication |

---

## Core Principles

### 1. Event-Driven Data Sync (Most Preferred)

Prefer publishing domain events over synchronous cross-service queries when a consumer just needs to know a fact changed.

**What this means:**
- Producers publish events (`OrderPlaced`, `CustomerUpdated`) to a broker; consumers subscribe independently
- Events are notifications of fact, not RPC calls — the producer never waits on a consumer
- Use the outbox pattern (write the event in the same transaction as the state change, publish asynchronously) to avoid dual-write inconsistency
- Prefer fat events (enough payload for common consumers) over thin events that force a callback to fetch details, unless payloads carry sensitive data

**Decision guide:**
- "Another system needs to react to something that happened" → event
- "I need to query current state right now" → synchronous API or a queryable read model kept in sync via CDC/events

---

### 2. Change Data Capture (CDC) for Real-Time Sync

Capture database changes at the source and propagate them downstream without impacting the source system's transactional workload.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Source DB  │    │    CDC       │    │  Target      │
│  (Postgres)  │───▶│  (Debezium)  │───▶│  (Kafka)     │
└──────────────┘    └──────────────┘    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Data Lake   │
                    │  or Warehouse│
                    └──────────────┘
```

**What this means:**
- Read the database's transaction/write-ahead log (WAL/binlog) instead of polling tables — near-zero load on the source
- Emit one event per row-level change (insert/update/delete), tagged with the operation type
- Use a durable, replayable log (Kafka, Kinesis, Pub/Sub) as the transport so consumers can catch up after downtime
- Land raw CDC events in a data lake for audit/replay, and materialize curated views for analytics

**When to use:**
- Real-time data sync between operational systems
- Event sourcing from legacy databases that can't be changed to publish events natively
- Near-real-time analytics pipelines and cache invalidation

---

### 3. Batch ETL / ELT for Bulk and Historical Data

Not all use cases are real-time; for e.g. bulk historical loads, large joins, and cost-sensitive analytics workloads are better served by scheduled batch pipelines.

**What this means:**
- ETL (transform before load) when the target enforces a strict schema or transformation logic is heavy
- ELT (load raw, transform in the warehouse) when the target has cheap compute (e.g. Snowflake, BigQuery) and transformations need to be replayable/auditable
- Orchestrate with a DAG-based scheduler (Airflow, Dagster) — pipelines are code, versioned, and testable
- Partition and checkpoint large loads so a failure mid-run resumes instead of restarting from zero

**When to use:**
- Nightly/hourly warehouse loads, historical backfills, large aggregations, ML training datasets

---

### 4. Reverse ETL (for Analytical data)

Push curated, aggregated data from the warehouse back into operational systems (CRM, support tools, marketing platforms) so business tools see analytics-derived fields.

**What this means:**
- The warehouse remains the source of truth for derived/aggregated metrics (e.g. `customer_ltv`, `churn_score`)
- A reverse ETL sync (Hightouch, Census, or a custom job) maps warehouse columns to operational-system fields
- Treat the destination system's write API as the contract — respect its rate limits and idempotency requirements
- Never let reverse ETL become a backdoor for operational writes that should go through the owning service's API instead

**When to use:**
- Feeding ML-derived scores or BI metrics into CRM/marketing tools that business teams already use

---

### 5. Schema Contracts and Compatibility

Every integration point — event, CDC stream, or batch extract — has an explicit, versioned schema. Consumers depend on the contract, not on the producer's internal representation.

**What this means:**
- Register schemas in a schema registry (Confluent Schema Registry, AWS Glue Schema Registry) before producers publish
- Enforce backward-compatible evolution by default (new optional fields, no removals/renames without a version bump)
- Breaking changes ship as a new topic/version; consumers migrate on their own schedule
- Validate producer payloads against the registered schema at publish time — fail fast, not downstream

**Compatibility modes:**
| Mode | Rule | Use When |
|------|------|----------|
| Backward | New schema can read old data | Default; consumers upgrade independently |
| Forward | Old schema can read new data | Producers upgrade ahead of consumers |
| Full | Both directions hold | High-stakes shared contracts with many consumers |

---

### 6. Idempotency and Exactly-Once Semantics

Distributed data pipelines redeliver messages. Design every consumer to produce the same result whether a message arrives once or ten times.

**What this means:**
- Assign every event a stable, unique key (event ID or natural business key) and dedupe on it at the consumer
- Prefer idempotent upserts (`INSERT ... ON CONFLICT UPDATE`) over blind inserts in downstream stores
- Where true exactly-once is required, use transactional producers/consumers (Kafka transactions) rather than hand-rolled dedup logic
- Make retries safe by default (at-least-once processing) — a retried write must never double-count or double-charge

---

### 7. Data Quality and Contract Testing

Bad data breaks trust faster than downtime. Validate data at every integration boundary, not just at the final dashboard.

**What this means:**
- Define expectations as code (Great Expectations, dbt tests, Soda) — null checks, uniqueness, referential integrity, freshness
- Run quality checks at ingestion (reject/quarantine bad records) and post-transform (catch regressions before they reach consumers)
- Track data freshness/SLA per pipeline (e.g. "table X is no more than 15 minutes stale") and alert on breach
- Treat data contracts like API contracts: producers commit to a schema and quality bar; violations are incidents

---

### 8. Data Mesh and Federated Ownership

Distribute data ownership across domains, treating data as a product rather than centralizing all integration within a single team.

| Principle | Implementation |
|-----------|-----------------|
| Domain ownership | Teams own and publish their own data products; no central "data team" bottleneck |
| Self-serve platform | Shared infrastructure as code (ingestion, cataloging, access) that any domain team can use |
| Federated governance | Central standards (schema, PII classification, SLAs) enforced locally by each domain |
| Product thinking | Every data product has an owner, documentation, discoverability, and a quality SLA |

**What this means:**
- Each domain publishes its data product (a well-documented, quality-assured dataset/event stream) through the self-serve platform
- A central catalog (DataHub, Amundsen, or a cloud-native equivalent) makes products discoverable across domains
- Governance rules (PII tagging, retention, access control) are defined centrally, applied automatically at publish time

**When to use:**
- Large organizations with many independent domains where a centralized data team becomes a bottleneck

---

### 9. Governance, Lineage, and Security

Every integration pipeline is auditable: who produced the data, who consumes it, what transformations were applied, and who is authorized to see it.

**What this means:**
- Capture lineage automatically (dbt, OpenLineage, or platform-native lineage) — never rely on tribal knowledge of "which job feeds this table"
- Classify data at the source (PII, PCI, PHI) and propagate that classification through every downstream transformation
- Encrypt data in transit (TLS) and at rest; apply row/column-level access control for sensitive fields, not just table-level grants
- Retention and deletion policies (e.g. GDPR right-to-erasure) must be enforceable across every copy the pipeline creates — track fan-out, not just the first hop

---

### 10. Resilience and Replayability

Every integration pipeline assumes its downstream or upstream dependency will be slow, unavailable, or delivering duplicates.

**What this means:**
- Use a durable, replayable log as the backbone (not fire-and-forget HTTP) so consumers can recover from an outage by replaying
- Apply dead-letter queues for records that fail transformation/validation — quarantine and alert, never silently drop
- Make backfills a first-class, tested operation — a pipeline that can only run forward can't recover from a bad deploy
- Monitor consumer lag (how far behind real-time a consumer is) as a primary health signal, not just error rate

---

## Operational Standards

| Practice | Requirement |
|----------|-------------|
| Schema registry | Every event/CDC schema registered and validated before publish |
| Lineage tracking | Every pipeline's source → transform → sink chain is discoverable |
| Freshness SLAs | Each pipeline declares and monitors a maximum staleness threshold |
| Dead-letter handling | Failed records are quarantined with alerting, never silently dropped |
| Idempotent consumers | All consumers safely handle redelivery/duplicates |
| PII classification | Sensitive fields tagged at source and propagated through every hop |
| Replay/backfill tested | Pipelines can reprocess historical data without manual intervention |

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Point-to-point integrations | N×N custom pipelines that don't scale as systems grow | Central event backbone / self-serve data platform |
| Polling the source database | Load on production systems, high latency, missed deletes | CDC off the transaction log |
| Schema-less events | Silent breaking changes, consumers fail at runtime | Schema registry with enforced compatibility |
| Dual writes without a transaction | State and event/cache fall out of sync on partial failure | Transactional outbox pattern |
| Reverse ETL as an operational backdoor | Bypasses the owning service's business rules/validation | Route operational writes through the service API |
| No dead-letter queue | Bad records silently dropped or crash the whole pipeline | Quarantine + alert on validation failure |
| Un-replayable pipelines | Can't recover from a bad deploy or downstream outage without manual backfill | Durable log + tested replay/backfill path |

---

## Summary

| Pattern | When to Use | Key Benefit |
|---------|-------------|-------------|
| Event-Driven Sync | Cross-service notification of state changes | Decoupled producers/consumers |
| CDC | Real-time sync off a database's transaction log | Near-real-time analytics without source load |
| Batch ETL/ELT | Bulk historical loads, heavy aggregations | Cost-efficient, replayable bulk processing |
| Reverse ETL | Push warehouse-derived data into operational tools | Business tools see analytics-derived fields |
| Schema Contracts | Any shared event/CDC/extract schema | Safe, independent producer/consumer evolution |
| Idempotent Consumers | Any at-least-once delivery pipeline | Safe redelivery, no double-processing |
| Data Quality Checks | Every ingestion and transform boundary | Catches bad data before it reaches consumers |
| Data Mesh | Large orgs with many independent domains | Scalable, federated data ownership |
| Governance & Lineage | Regulated or PII-bearing data | Auditability and compliance |
