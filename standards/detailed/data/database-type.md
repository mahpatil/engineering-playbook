# Database Type Selection Standards

Standards for choosing and operating the right database for each workload.

---

## Why This Matters

Selecting the wrong database type is one of the most expensive architectural mistakes a team can make. It shows up as slow queries, schema migrations that take hours, scaling issues, higher costs, or correctness bugs in financial data. Unlike application code, a database migration is painful, risky, and disruptive — re-platforming a live system under load is a multi-month effort. Get this right once, at design time.

The cost of a wrong database choice compounds: your schema design, your API contracts, your operational tooling, and your team's expertise all build on top of the database type. A document store chosen for convenience will force you to reconstruct joins in application code; a relational database chosen for familiarity will become a bottleneck at write-heavy IoT scale.

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Correctness** | ACID transactions prevent financial inconsistencies, double-charges, and inventory errors |
| **Scale** | Horizontal NoSQL databases handle write volumes that vertical relational scaling cannot |
| **Velocity** | Schema-flexible document stores let product teams iterate without migration ceremonies |
| **Cost** | Right-sized stores avoid over-provisioning; using Postgres where Redis is sufficient wastes resources |
| **Data Integrity** | Enforced constraints at the database layer beat application-level discipline at scale |
| **Operability** | Familiar tooling reduces MTTR; a database your SRE team cannot debug is a liability |

---

## Core Decision: Relational vs NoSQL

Start here. This is the highest-leverage database decision one can make.

| Factor | Choose Relational (PostgreSQL, MySQL) | Choose NoSQL |
|--------|---------------------------------------|--------------|
| **Data model** | Structured, tabular, normalized | Hierarchical, nested, variable schema |
| **Relationships** | Complex multi-entity joins | Few joins; data denormalized per access pattern |
| **Consistency** | Strong ACID required (payments, inventory) | Eventual or tunable consistency acceptable |
| **Query patterns** | Ad-hoc queries, analytics, reporting | Known, fixed access patterns defined upfront |
| **Scale** | Vertical + moderate horizontal (read replicas) | Horizontal scale to millions of writes/sec |
| **Schema** | Stable, well-understood domain | Evolving, heterogeneous, or sparse attributes |
| **Transactions** | Multi-row, multi-table critical | Single-entity or avoidable |

**Default to relational** unless you have a clear, demonstrated reason not to. PostgreSQL handles far more than most teams expect — JSONB columns, full-text search, time-series via partitioning, and horizontal reads via Citus or read replicas.

---

## NoSQL Types — What Each Solves and How to Use It

### Document Stores
**What:** JSON-like documents stored and retrieved as a unit. No fixed schema. Rich query support within a document.

**Why:** Product catalogs, user profiles, CMS content, and order records have variable attributes that don't map cleanly to a fixed table schema. Document stores let each record carry its own shape.

**How:**
- Model one aggregate root per document (e.g., an order with all its line items embedded)
- Query patterns must be known upfront — design indexes to match your reads
- Avoid cross-document joins; if you need them regularly, reconsider relational

**Use:** MongoDB, Firestore, DynamoDB (document mode)
**Avoid when:** Cross-document referential integrity is required or strong consistency is non-negotiable

---

### Key-Value Stores
**What:** Simple map of key → value with O(1) lookup. No query language; you get exactly what you ask for by key.

**Why:** Session management, rate limiting, feature flags, and caching need microsecond latency at high throughput. A relational database carrying this traffic wastes join overhead on data that has no relationships.

**How:**
- Design keys to be self-describing: `session:{userId}`, `ratelimit:{ip}:{window}`
- Always set TTL — key-value stores fill up fast without expiry
- Use Redis data structures (sorted sets, streams, pub/sub) before adding a second database

**Use:** Redis, Valkey, DynamoDB (key-value mode)
**Avoid when:** You need to query by value attributes, not just key

---

### Wide-Column Stores
**What:** Data organized by row key with flexible columns per row. Designed for massive write throughput with time-ordered access.

**Why:** IoT telemetry, audit logs, and activity feeds generate millions of writes per second. Relational databases cannot sustain this without sharding complexity. Wide-column stores are built for append-heavy, time-ordered workloads.

**How:**
- Partition key is everything: it determines physical co-location and query routing
- Avoid hotspot partition keys (e.g., a single device ID receiving all writes) — use composite keys with time bucketing
- Model for your most common read pattern; wide-column stores are hostile to arbitrary queries

**Use:** Cassandra, Bigtable, ScyllaDB
**Avoid when:** Queries span multiple dimensions or dataset is small enough for Postgres with partitioning

---

### Graph Databases
**What:** Nodes and edges as first-class primitives. Graph traversal is efficient and native.

**Why:** Fraud detection, social graphs, and recommendation engines require multi-hop relationship traversal. In a relational database this becomes a recursive CTE or multiple self-joins — expensive and hard to reason about. Graph databases make relationship traversal cheap.

**How:**
- Model entities as nodes, relationships as edges with properties
- Write graph queries (Cypher, Gremlin) against relationship-centric questions: "who knows who", "what did this account touch in the last 24 hours"
- Graph databases are not general-purpose; keep your system of record in a relational store and sync to graph for relationship queries

**Use:** Neo4j, Amazon Neptune
**Avoid when:** The domain is not fundamentally relationship-centric; team has no graph query language experience

---

### Time-Series Databases
**What:** Optimized storage and compression for timestamped data. Efficient range scans and downsampling aggregations.

**Why:** Metrics, monitoring, and financial tick data are written in high-volume, time-ordered streams and queried by time range. General-purpose databases waste storage on repeated timestamps and cannot efficiently downsample millions of rows.

**How:**
- Retention policies and downsampling are first-class features — configure them to control storage cost
- Design tags/labels carefully: they are your query dimensions (by service, region, sensor ID)
- Use TimescaleDB when you need SQL compatibility on top of time-series compression

**Use:** InfluxDB, TimescaleDB, Prometheus (for metrics)
**Avoid when:** Application data has no time dimension as its primary access pattern

---

### Search Engines
**What:** Inverted indexes optimized for full-text search, faceted filtering, and relevance ranking.

**Why:** Product search, log analytics, and content discovery require queries that relational `LIKE` clauses cannot serve — stemming, fuzzy matching, relevance scoring, and faceted aggregations over millions of documents.

**How:**
- Never use a search engine as a system of record — it is a derived, queryable index of your primary data
- Sync from your primary database via events (CDC or outbox pattern), not dual-writes
- Define index mappings explicitly; auto-mapping from unknown documents creates unmaintainable indexes

**Use:** Elasticsearch, OpenSearch
**Avoid when:** Strong consistency or primary data ownership is required

---

## NoSQL Design Checklist

Work through this before writing any schema. NoSQL schema mistakes are costly to fix in production.

- [ ] **Access patterns first** — list every query your application will run before designing the schema. The schema serves the queries, not the domain model.
- [ ] **Denormalize intentionally** — duplicate data to serve read patterns. Document the duplication and the source of truth explicitly.
- [ ] **Partition key distribution** — verify that your partition key distributes load evenly across partitions. A single hot partition eliminates horizontal scale.
- [ ] **Hotspot mitigation** — for counters, trending items, or global aggregates, use write sharding (random suffix + periodic aggregation) or offload to Redis.
- [ ] **Consistency documented per entity** — for each entity, state the consistency requirement: strong / eventual / read-your-writes. Wire this to read/write settings.
- [ ] **No joins mindset** — if you are designing a join, stop. Either embed the related data or move to a relational model.
- [ ] **TTL configured** — sessions, OTPs, caches, and short-lived events must have TTL set at the database level. Never rely on application cleanup alone.
- [ ] **Schema evolution plan** — NoSQL does not enforce schema. Define your strategy: additive-only changes, version fields for breaking changes, backfill scripts as separate jobs.
- [ ] **Capacity modeled** — model your read/write capacity (DynamoDB RCU/WCU, Cassandra throughput, Redis memory) before launch.
- [ ] **Index cost known** — secondary indexes in NoSQL are write-amplifying. Add only for confirmed, frequent access patterns.

---

## Relational vs NoSQL Design — Key Differences

| Concern | Relational | NoSQL |
|---------|------------|-------|
| **Schema design** | Model the domain (3NF); queries adapt to schema | Model the queries (access-pattern-first); schema adapts to queries |
| **Relationships** | Foreign keys + joins at query time | Embed nested data or duplicate reference data at write time |
| **Transactions** | Multi-table ACID built in | Single-entity atomic; multi-entity requires sagas or application-level coordination |
| **Querying** | Flexible ad-hoc SQL | Predefined query paths; off-pattern queries are expensive or impossible |
| **Scaling** | Scale up first; horizontal sharding is complex | Horizontal scale is a first-class primitive |
| **Consistency** | Default strong consistency | Explicit choice per operation: strong / bounded staleness / eventual |
| **Migrations** | ALTER TABLE with tooling (Flyway, Liquibase) | Additive-only (no dropping/renaming); versioning in application code; no DB-layer enforcement |
| **Data integrity** | Enforced by DB (NOT NULL, FK, CHECK) | Enforced by application — discipline required |

---

## Polyglot Persistence Rules

Using multiple databases in one system is normal and often correct. These rules prevent it from becoming an operational liability.

1. **One store owns each entity** — no entity is the source of truth in two databases simultaneously. Caches and search indexes are derived, not authoritative.
2. **Sync via events, not dual-writes** — if a record in Postgres must appear in Elasticsearch, publish an event and let a consumer update the index. Dual-write from the application creates consistency gaps.
3. **Stale reads documented** — if a secondary store (search index, cache) can be stale, document the staleness window. Surface it in API responses where it affects correctness.
4. **Operations must be able to run it** — don't adopt a database your team cannot operate or debug. Prefer managed services (RDS, DynamoDB, Atlas, Elastic Cloud) over self-managed unless you have dedicated DBA capacity.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Using NoSQL because it's "modern" | Eventual consistency bugs in financial data, join pain at query time | Default to relational; only switch when you have a demonstrated need |
| Shared database between services | Couples deployments, prevents independent schema evolution | Database per service or schema per service |
| Relational DB for session storage | Unnecessary load on your system of record | Redis or Valkey for ephemeral, high-throughput key-value |
| Full-text search via SQL LIKE | Slow, no relevance ranking, no stemming | Elasticsearch or OpenSearch as a derived search index |
| Skipping partition key design in Cassandra/DynamoDB | Hot partitions that defeat horizontal scale | Model partition keys against access patterns before writing schema |
| Treating search engine as primary store | Data loss risk, no strong consistency | Search engine indexes primary data; never writes to it directly |
