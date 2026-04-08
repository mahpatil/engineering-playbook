# Data Storage Standards — NoSQL vs Relational

This file governs all database and storage decisions.

---

## NoSQL vs Relational — How to Choose

Start here. Pick the wrong database type and you pay the cost for the lifetime of the product.

| Factor | Choose Relational (PostgreSQL, MySQL) | Choose NoSQL |
|---|---|---|
| **Data model** | Structured, tabular, normalized | Hierarchical, nested, variable schema |
| **Relationships** | Complex multi-entity joins | Few joins; data denormalized per access pattern |
| **Consistency** | Strong ACID required (payments, inventory) | Eventual or tunable consistency acceptable |
| **Query patterns** | Ad-hoc queries, analytics, reporting | Known, fixed access patterns |
| **Scale** | Vertical + moderate horizontal (read replicas) | Horizontal scale to millions of writes/sec |
| **Schema** | Stable, well-understood domain | Evolving, heterogeneous, or sparse attributes |
| **Team** | SQL expertise in-house | NoSQL ops experience available |
| **Transactions** | Multi-row, multi-table critical | Single-entity or can be avoided |

**Default to relational** unless you have a clear reason not to. PostgreSQL handles more than most teams think — JSONB, full-text search, time-series via partitioning, and horizontal reads via Citus.

---

## Types of NoSQL — When to Use

| Type | Best For | Avoid When | Examples |
|---|---|---|---|
| **Document** | User profiles, product catalogs, CMS content, event records with variable attributes | Heavy cross-document joins required; strong referential integrity needed | MongoDB, Firestore, DynamoDB |
| **Key-Value** | Session storage, caching, rate limiting, feature flags, leaderboards | Rich querying on values; complex data relationships | Redis, DynamoDB, Valkey |
| **Wide-Column** | Time-ordered write-heavy workloads, IoT telemetry, audit logs, activity feeds at scale | Complex queries across multiple dimensions; small datasets | Cassandra, Bigtable, ScyllaDB |
| **Graph** | Social graphs, fraud detection, recommendation engines, knowledge graphs, network topology | Non-relationship-heavy queries; team unfamiliar with graph query languages | Neo4j, Amazon Neptune |
| **Time-Series** | Metrics, monitoring, financial tick data, sensor readings, log aggregation | General-purpose application data; infrequent time-based queries | InfluxDB, TimescaleDB, Prometheus |
| **Search** | Full-text search, faceted filtering, log analytics, geospatial queries | Primary source of truth; strong consistency required | Elasticsearch, OpenSearch |

> **Tip:** DynamoDB is both Document and Key-Value. Redis can be Key-Value, Search (RediSearch), and Time-Series. Polyglot is normal — but each store must own a specific concern.

---

## NoSQL Design Checklist

Work through this before writing any schema.

- [ ] **Access patterns first** — list every query your app will run before designing the schema. NoSQL schema is read-optimized; your queries are the spec.
- [ ] **Denormalize intentionally** — duplicate data to serve read patterns. Accept write amplification as the cost. Document the duplication explicitly.
- [ ] **Partition key design** — partition keys must distribute load evenly. Avoid user ID as a bare partition key if a small set of power users will dominate traffic.
- [ ] **Hotspot avoidance** — if a key will receive disproportionate traffic (trending post, global counter), use write sharding (append a random suffix, aggregate later) or a cache layer.
- [ ] **Consistency trade-offs documented** — for each entity, state the consistency requirement (strong / eventual / read-your-writes). Wire that to your read/write settings.
- [ ] **No joins mindset** — if you're designing a join, stop. Either embed the related data or rethink whether this belongs in a relational database.
- [ ] **TTL / expiry set** — short-lived data (sessions, OTPs, caches, events) must have TTL configured. Never rely on application-level cleanup alone.
- [ ] **Schema evolution plan** — NoSQL does not enforce schema. Define a migration strategy: additive changes only, version fields for breaking changes, backfill scripts in separate jobs.
- [ ] **Capacity planning** — model your RCU/WCU (DynamoDB), throughput (Cassandra), or memory (Redis) before launch. Surprises here are expensive and operational.
- [ ] **Index cost awareness** — secondary indexes in NoSQL are writes, not free lookups. Add indexes only for confirmed access patterns.

---

## Key Differences from Relational Design

| Concern | Relational Approach | NoSQL Approach |
|---|---|---|
| **Schema design** | Model the domain (3NF normalization); queries adapt to schema | Model the queries (access pattern first); schema adapts to queries |
| **Relationships** | Foreign keys + joins at query time | Embed nested data or duplicate reference data at write time |
| **Transactions** | Multi-table ACID transactions built in | Single-entity atomic; multi-entity requires application-level sagas or two-phase commit patterns |
| **Querying** | Flexible ad-hoc SQL; optimizer handles execution plan | Predefined query paths; queries outside design patterns are expensive or impossible |
| **Scaling** | Scale up first; horizontal sharding is complex | Designed for horizontal scale; partitioning is a first-class primitive |
| **Consistency** | Default strong consistency; read your own writes trivially | Explicit choice per operation: strong, bounded staleness, eventual |
| **Migrations** | ALTER TABLE with downtime windows or online DDL tools | Additive-only; versioning in application code; no enforcement at DB layer |
| **Data integrity** | Enforced by DB (NOT NULL, FK, CHECK constraints) | Enforced by application layer — discipline required |
| **Tooling** | Mature: ORMs, query builders, migration frameworks | Younger ecosystem; varies by database; fewer standards |

---

## Polyglot Persistence Rules

Using multiple databases in one system is normal. These rules prevent it from becoming a liability.

1. **One store owns each entity** — no entity is the source of truth in two databases simultaneously.
2. **Sync via events, not direct writes** — if a record in Postgres must appear in Elasticsearch, publish an event; don't dual-write from the application.
3. **Stale reads are documented** — if a secondary store (search index, cache) can be stale, document the staleness window and surface it in API responses where relevant.
4. **Operations must own it** — don't adopt a database your SRE team cannot operate. A managed service (RDS, DynamoDB, Atlas, Elastic Cloud) is strongly preferred over self-managed unless you have dedicated DBA capacity.
