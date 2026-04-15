# Data Architecture

This document covers foundational data architecture patterns for building scalable systems: database design in microservices, data lakes, analytics use cases, and AI/ML data patterns.

---

## 1. Database Design in Microservices

### 1.1 Database per Service Pattern

Each microservice owns its data entirely. No shared databases between services.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Orders     │     │  Customers  │     │  Payments   │
│  Service    │     │  Service    │     │  Service    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
   ┌───┴───┐           ┌───┴───┐           ┌───┴───┐
   │Orders │           │Cust-  │           │Pay-   │
   │DB     │           │omersDB│           │mentsDB│
   └───────┘           └───────┘           └───────┘
```

**When to use:**
- Services have independent scaling needs
- Different data models per service
- Teams need full ownership of their data

**Avoid when:**
- Services are tightly coupled by data
- Cross-service queries are frequent (redesign boundaries instead)

---

### 1.2 Saga Pattern for Distributed Transactions

Orchestrate multi-service operations using coordinated local transactions.

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│Order    │───▶│Payment │───▶│Inventory│
│Service │    │Service │    │Service  │
└─────────┘    └─────────┘    └─────────┘
     ▲              │              │
     └──────────────┴──────────────┘
         Compensating Transactions
            (rollback on failure)
```

**Implementation:**
```python
# Orchestrator-based saga
class OrderSaga:
    async def execute(self, order):
        try:
            # Step 1: Create order (pending)
            order = await self.order_service.create(order)
            
            # Step 2: Reserve payment
            await self.payment_service.reserve(order.payment_info)
            
            # Step 3: Reserve inventory
            await self.inventory_service.reserve(order.items)
            
            # Step 4: Confirm order
            await self.order_service.confirm(order.id)
            
        except Exception as e:
            await self.compensate(order)
            raise
```

**Compensating actions must be:**
- Idempotent (safe to retry)
- Reversible where possible
- Logged for audit

---

### 1.3 CQRS Pattern

Separate read and write models for optimal performance on each path.

```
 Writes                    Reads
───────▶              ◀──────
  Command                   Query
    │                        │
    ▼                        ▼
┌─────────┐            ┌─────────┐
│ Write   │   Event     │ Read    │
│ Model   │───────────▶│ Model   │
│ (OLTP)  │   Stream    │ (OLAP)  │
└─────────┘            └─────────┘
```

**Use cases:**
- Different read/write scaling requirements
- Complex query patterns (reporting, dashboards)
- Eventual consistency is acceptable

**Read models:**
- Materialized views
- Projections
- Denormalized for specific access patterns

---

### 1.4 Event Sourcing

Store state changes as a sequence of events, not current state.

```
┌─────────────────────────────────────┐
│           Event Store               │
├─────────────────────────────────────┤
│ OrderCreated     {id, items, ...}  │
│ ItemAdded       {orderId, item}    │
│ PaymentApplied  {orderId, amount}   │
│ OrderShipped    {orderId, track}   │
│ OrderCompleted {orderId}          │
└─────────────────────────────────────┘
```

**Benefits:**
- Complete audit trail
- Time-travel queries (state at any point)
- Easy to rebuild projections

**Trade-offs:**
- Event schema evolution required
- Initial load can be slow
- More storage (events vs state)

---

## 2. Data Lake Architecture

### 2.1 Data Lake Overview

Centralized repository storing raw data at any scale.

```
┌──────────────────────────────────────────────────────┐
│                   Data Lake                         │
├──────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐              │
│  │  Raw    │  │ Cleaned │  │ Curated │              │
│  │  Zone   │──▶ Zone   │──▶ Zone   │              │
│  │ (Bronze)│  │ (Silver)│  │ (Gold)  │              │
│  └─────────┘  └─────────┘  └─────────┘              │
└──────────────────────────────────────────────────────┘
```

| Zone | Purpose | Format | Access |
|------|---------|--------|--------|
| Raw (Bronze) | Ingested as-is | Parquet/ORC | Data engineers |
| Cleaned (Silver) | Validated, deduplicated | Parquet | Analysts |
| Curated (Gold) | Business-ready | Delta/Iceberg | BI/ML |

---

### 2.2 ETL vs ELT

**ELT (Preferred for cloud data lakes):**
```
Source → Extract → Load → Transform (in warehouse)
         │          │
         ▼          ▼
     Raw Zone    Transformed
```

**When to use ELT:**
- Large data volumes
- Cloud data warehouse (Snowflake, BigQuery, Redshift)
- Transform capacity in warehouse exceeds extraction cost

---

### 2.3 Data Lake Technologies

| Layer | Technologies | Use Case |
|-------|---------------|---------|
| Storage | S3, GCS, ADLS, HDFS | Object storage |
| Format | Parquet, ORC, Delta, Iceberg | Columnar, ACID |
| Engine | Spark, Flink, DuckDB | Processing |
| Catalog | Hive Metastore, Unity Catalog | Schema discovery |
| Governance | LakeFormation, Datahub | Access control |

---

### 2.4 Data Lake Best Practices

- **Partition by date/entity** — Most queries filter by time
- **Use columnar formats** — Parquet for analytics
- **Separate hot/cold data** — Tiered storage for cost
- **Enforce schema on write** — Prevent bad data ingestion
- **Implement lifecycle policies** — Archive/delete old data

---

## 3. Analytics Use Cases

### 3.1 Analytics Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
��  Source     │     │   Data     │     │  Analytics  │
│  Systems    │────▶│   Lake     │────▶│  Warehouse │
│             │     │            │     │            │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Stream    │     │ Dashboard/ │
                    │   Processing│     │   Reports  │
                    └─────────────┘     └─────────────┘
```

### 3.2 Batch Analytics

| Use Case | Pattern | Tools |
|----------|---------|-------|
| Daily reports | Scheduled batch | Spark, dbt |
| Business KPIs | Aggregations | SQL, Looker |
| Ad-hoc analysis | Interactive queries | Databricks, BigQuery |

**Example: Daily Revenue Report**
```sql
SELECT 
    DATE(created_at) as day,
    currency,
    SUM(amount) as revenue,
    COUNT(*) as transactions
FROM orders
WHERE created_at >= DATE_TRUNC(CURRENT_DATE, DAY)
GROUP BY DATE(created_at), currency
```

---

### 3.3 Streaming Analytics

| Use Case | Latency | Tools |
|----------|---------|-------|
| Real-time dashboards | < 1 sec | Flink, Spark Streaming |
| Anomaly detection | < 10 sec | Kafka Streams, ksqlDB |
| Alerting | < 30 sec | Stream processing |

**Example: Sliding Window Revenue**
```sql
SELECT 
    window_start,
    SUM(amount) as revenue
FROM TUMBLE(orders, DESCRIPTOR(created_at), INTERVAL '1' HOUR)
GROUP BY window_start
HAVING SUM(amount) > 10000
```

---

### 3.4 Common Analytics Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| Rolling aggregation | Last N periods | 7-day moving average |
| Cumulative | Running total | YTD revenue |
| Funnel analysis | Conversion steps | Signup → Activation → Paid |
| Cohort analysis | Group by time | Monthly retention by signup cohort |
| A/B test analysis | Statistical comparison | Control vs variant conversion |

---

## 4. AI/ML Data Patterns

### 4.1 ML Data Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Source    │     │   Feature   │     │    ML       │
│   Data      │────▶│   Store     │────▶│   Training  │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  Raw data   │     │  Features  │     │   Model     │
  │  (Bronze)   │     │  (Online/  │     │  Registry   │
  │             │     │   Offline) │     │             │
  └─────────────┘     └─────────────┘     └─────────────┘
```

### 4.2 Feature Store Design

| Feature Type | Storage | Access Pattern |
|--------------|---------|----------------|
| Batch features | Offline store (Parquet) | Training, backfill |
| Streaming features | Online store (Redis) | Real-time inference |

**Example: Feature Schema**
```yaml
features:
  - name: user_total_orders
    type: int64
    source: orders_db
    sql: "SELECT COUNT(*) FROM orders WHERE user_id = {user_id}"
    update_frequency: daily
    
  - name: user_avg_order_value
    type: float64
    source: orders_db
    sql: "SELECT AVG(amount) FROM orders WHERE user_id = {user_id}"
    update_frequency: daily
```

---

### 4.3 Training Data Patterns

| Pattern | Use Case | Format |
|---------|----------|--------|
| Full refresh | Small datasets | CSV, Parquet |
| Incremental | Large datasets | Delta, Iceberg |
| Streaming | Real-time ML | Kafka, Kinesis |

**Data Split Strategy:**
```
┌─────────────────────────────────┐
│         Training Data           │
├──────────────┬──────────────────┤
│   Training   │    Validation    │
│    (70-80%)  │     (20-30%)      │
│              ├──────────────────┤
│              │     Test         │
│              │   (holdout)      │
└──────────────┴──────────────────┘
```

---

### 4.4 MLOps Data Patterns

| Concern | Pattern | Implementation |
|---------|---------|----------------|
| Data versioning | Dataset versioning | DVC, Delta |
| Feature consistency | Feature store | Feast, Tecton |
| Data quality | Contract testing | Great Expectations |
| Data lineage | Tracking | MLflow, Kubeflow |

---

### 4.5 Common AI/ML Data Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| Label encoding | Categorical to numeric | High/Med/Low → 0/1/2 |
| One-hot encoding | Binary columns | Color → R/G/B columns |
| Normalization | Scale to 0-1 | (x - min) / (max - min) |
| Missing imputation | Fill missing values | Mean, median, forward fill |
| Time-based features | Temporal engineering | Day of week, hour, month |

---

## 5. Integration Patterns

### 5.1 CDC (Change Data Capture)

Capture database changes in real-time.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Source DB   │    │    CDC       │    │  Target      │
│  (Postgres)   │───▶│  (Debezium)  │───▶│  (Kafka)     │
└──────────────┘    └──────────────┘    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Data Lake   │
                    │  or Warehouse│
                    └──────────────┘
```

### 5.2 Data Mesh Principles

| Principle | Implementation |
|-----------|----------------|
| Domain ownership | Teams own their data products |
| Self-serve platform | Infrastructure as code |
| Federated governance | Shared standards, local execution |
| Product thinking | Data as a product with users |

---

## 6. Decision Framework

Use this decision tree to choose the right pattern:

```
Start: What is your primary need?
│
├─▶ Transactional integrity
│   └─▶ Use Database per Service + ACID
│
├─▶ Scalable reads
│   ├─▶ Different read/write patterns
│   │   └─▶ Use CQRS
│   └─▶ High-volume simple reads
│       └─▶ Use NoSQL (DynamoDB, Cassandra)
│
├─▶ Analytics/Reporting
│   └─▶ Use Data Lake + Warehouse
│
├─▶ AI/ML data
│   └─▶ Use Feature Store + Versioning
│
└─▶ Event-driven
    └─▶ Use Event Sourcing + CDC
```

---

## Summary

| Pattern | When to Use | Key Benefit |
|---------|-------------|-------------|
| Database per Service | Microservices with independent data | Loose coupling |
| CQRS | Different read/write patterns | Performance optimization |
| Data Lake | Analytics at scale | Cost-effective storage |
| Feature Store | ML training/inference | Consistent features |
| Event Sourcing | Audit trail, time-travel | Complete history |
| CDC | Real-time data sync | Near-real-time analytics |