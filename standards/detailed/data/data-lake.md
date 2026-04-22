# Data Lake Architecture Standards

Standards for designing, building, and operating a data lake for analytics, reporting, and ML workloads.

---

## Why This Matters

Operational databases are optimized for transactions — they serve fast, narrow reads and writes for live systems. They are not designed to answer questions like "what was our revenue trend by region over the last 18 months by product category?" Running that kind of query against a live PostgreSQL cluster causes lock contention, degrades response times for real users, and still returns in minutes rather than seconds.

A data lake solves a different problem: it accumulates all raw data from across your systems, preserves history, and makes it available for large-scale analytical workloads without touching production systems. Without it, analytics teams either query production directly (risky), build separate reports in each system (fragmented), or wait on engineering to export data manually (slow).

The failure mode without a data lake: teams make decisions on stale exports, shadow spreadsheets diverge from the source of truth, and ML teams spend 80% of their time wrangling data instead of building models.

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Analytical Independence** | Analysts query historical data without impacting production systems |
| **Single Source of Truth** | All business data in one place eliminates conflicting spreadsheet versions |
| **ML Readiness** | Clean, versioned datasets that feature engineering pipelines can consume reliably |
| **Cost Efficiency** | Object storage (blob/S3) is orders of magnitude cheaper than analytical database compute for cold data |
| **Audit and Compliance** | Immutable raw zone preserves original records for regulatory review |
| **Data Product Enablement** | Teams can publish and consume data assets without bespoke pipelines per consumer |

---

## Core Architecture: Bronze → Silver → Gold

Every data lake is organized into progressive refinement zones. Raw data flows in at Bronze, gets cleaned at Silver, and is made business-ready at Gold. Each zone has different consumers, quality guarantees, and access controls.

```
┌─────────────────────────────────────────────────────────────┐
│                         Data Lake                           │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │    Bronze    │──▶│    Silver    │──▶│     Gold     │    │
│  │  (Raw Zone)  │   │ (Cleaned)    │   │  (Curated)   │    │
│  └──────────────┘   └──────────────┘   └──────────────┘    │
│   As-is ingestion    Validated,         Business-ready,     │
│   No transforms      deduplicated,      aggregated,         │
│   Immutable          type-corrected     domain-modeled      │
└─────────────────────────────────────────────────────────────┘
```

---

### Bronze Zone (Raw)

**What it is:** An exact copy of source data, ingested as-is. No transformations. Immutable after write.

**Why:** You cannot know upfront what questions you will need to answer in the future. Preserving raw data means you can reprocess history when requirements change — without going back to source systems. It also provides an audit trail for compliance.

**How to implement:**
- Write in columnar format (Parquet, ORC) — even for raw data, this reduces storage cost and scan time compared to CSV or JSON
- Partition by ingestion date: `year=2025/month=04/day=22/` — this is your most common filter
- Never delete or modify files after writing. If source data is corrected, write a new version alongside the original
- Capture source metadata: ingestion timestamp, source system, batch ID
- Access is restricted to data engineering — not exposed to analysts or downstream consumers

---

### Silver Zone (Cleaned)

**What it is:** Validated, deduplicated, type-corrected data. Schema enforced. Bad records quarantined with error details.

**Why:** Raw data is messy — duplicates from retry logic, type mismatches from schema drift, nulls in required fields. Cleaning once at Silver means every downstream consumer gets the same quality baseline rather than each team implementing their own cleaning logic independently.

**How to implement:**
- Enforce schema on write using Delta Lake or Apache Iceberg — schema evolution is tracked and explicit
- Deduplicate using a deterministic unique key per record (event ID, transaction ID) — not arrival time
- Quarantine bad records: write invalid rows to a separate `_quarantine/` partition with failure reason and source metadata
- Apply standard data types: timestamps in UTC ISO 8601, currency as integer cents (not float), enums as canonical strings
- Idempotent processing: re-running a pipeline over the same input must produce the same output

---

### Gold Zone (Curated)

**What it is:** Aggregated, business-modeled datasets ready for consumption by analysts, dashboards, and ML pipelines.

**Why:** Analysts should not need to understand raw event schemas or write complex joins to answer business questions. Gold zone pre-joins, pre-aggregates, and exposes data in the language of the business — dimensions, facts, metrics.

**How to implement:**
- Model as dimensional tables (star or snowflake schema) for BI tool compatibility
- Pre-aggregate common metrics: daily revenue, weekly active users, monthly cohort retention
- Expose as views or materialized tables in a query engine (Databricks, Synapse, BigQuery, Athena)
- Document every table: owner, refresh cadence, SLA, and which business questions it answers
- Partition on the most common filter dimension (date, region, product line)

---

## Ingestion Patterns

| Pattern | When to Use | How |
|---------|-------------|-----|
| **Batch** | Daily reports, financial summaries, non-time-sensitive analytics | Scheduled jobs (Airflow, Azure Data Factory, dbt) on a cadence |
| **Micro-batch** | Near-real-time dashboards, hourly aggregates | Spark Structured Streaming or Flink with small batch intervals |
| **Streaming** | Fraud detection, live dashboards, operational alerting | Kafka → Spark/Flink → Bronze landing in near-real-time |
| **Change Data Capture (CDC)** | Replicating operational databases without touching production | Debezium or Azure DMS captures row-level changes from Postgres/SQL |

**Default to batch** unless the business requires near-real-time freshness. Streaming adds operational complexity — use it when latency matters, not as a default.

---

## Storage and Format Standards

**Why columnar formats:** Analytics queries read a small number of columns across millions of rows. Row-based formats (CSV, JSON) require reading all columns even when only two are needed. Parquet and ORC skip unused columns, reducing I/O by 80–95% for typical analytical queries.

**Why Delta Lake or Iceberg over raw Parquet:**
- ACID transactions on object storage — concurrent writes without corruption
- Time travel: query data as it existed at any point in history
- Schema evolution: add columns without rewriting all files
- Efficient small-file compaction built in

| Format | Use Case | Notes |
|--------|----------|-------|
| Parquet | Bronze and Silver | Efficient columnar storage; widely supported |
| Delta Lake | Silver and Gold | ACID + time travel + schema enforcement |
| Apache Iceberg | Silver and Gold | Open standard; works across engines (Spark, Flink, Trino) |
| ORC | Legacy Hive compatibility | Prefer Parquet or Delta for new workloads |

---

## Partitioning Strategy

**Why:** Object storage has no index. The only way to avoid full scans is to organize files so that queries can skip entire folders. Partitioning is how you give the query engine that skip-ability.

**How:**
- Always partition Bronze and Silver by ingestion date: `dt=2025-04-22/`
- Partition Gold by the most common filter dimension for that table — usually date, sometimes region or product
- Avoid high-cardinality partition keys (user ID, session ID) — creates millions of tiny partitions that slow down metadata operations
- Target file sizes of 128MB–1GB per Parquet file. Use compaction jobs to merge small files created by streaming writes

---

## Data Quality Standards

**Why:** Downstream decisions — business reports, ML models, financial reconciliation — are only as good as the data feeding them. Silent data quality failures are worse than visible pipeline failures because they produce wrong answers that look right.

**How:**
- Define data quality rules as code alongside pipeline code — not in a spreadsheet
- Validate on ingest at Silver: null checks, range checks, referential integrity, uniqueness
- Fail loudly for schema-breaking changes; quarantine and alert for row-level quality issues
- Track quality metrics: completeness rate, duplicate rate, late-arrival rate per source
- Set SLAs on freshness: Gold tables used for dashboards must be updated within N hours of day close

---

## Access Control Model

| Zone | Who Can Read | Who Can Write |
|------|-------------|---------------|
| Bronze | Data engineering only | Ingestion pipelines only |
| Silver | Data engineering, ML engineering | Transform pipelines only |
| Gold | Analysts, BI tools, ML consumers | Transform pipelines only; no direct writes |

- Use managed identities or service principals — no shared credentials
- Encrypt at rest (AES-256) and in transit (TLS)
- Audit all reads in Gold for compliance workloads

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Querying Bronze directly for reports | Analysts work on raw, uncleaned data; different cleaning logic per team | Force analytical access through Gold |
| Mutating Bronze records | Lose audit trail; cannot replay history correctly | Treat Bronze as append-only; corrections are new records |
| No partitioning on large tables | Full table scans that take hours and cost more | Always partition by date; add a second partition key for high-volume tables |
| CSV/JSON in long-term storage | 5–10x storage cost, slow scans, no schema enforcement | Parquet or Delta on ingest |
| Skipping schema enforcement on Silver | Bad data propagates silently to Gold and then to decisions | Enforce schema on every Silver write |
| Rebuilding Gold from Gold | Cascading errors propagate; lineage breaks | Always rebuild derived tables from Silver, not from other Gold tables |
| One massive Gold table for everything | Query performance degrades; hard to reason about | Separate tables per business domain and access pattern |
