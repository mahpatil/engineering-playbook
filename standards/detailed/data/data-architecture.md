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

**Key points:**
- Orchestrate steps across services
- If any step fails, compensate (undo) all previous steps
- Each compensation must be idempotent (safe to retry)

---

### 1.3 CQRS Pattern

Separate read and write models for optimal performance on each path.

```
 Writes                    Reads
──────▶              ◀──────
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

---

## 2. Data Lake Architecture

### 2.1 Data Lake Overview

Centralized repository storing raw data at any scale.

```
┌──────────────────────────────────────────────────────┐
│                   Data Lake                         │
├──────────────────────────────────────────────────────┤
│  ┌──────��──┐  ┌─────────┐  ┌─────────┐              │
│  │  Raw    │  │ Cleaned │  │ Curated │              │
│  │  Zone   │──▶ Zone   │──▶ Zone   │              │
│  │ (Bronze)│  │ (Silver)│  │ (Gold)  │              │
│  └─────────┘  └─────────┘  └─────────┘              │
└──────────────────────────────────────────────────────┘
```

| Zone | Purpose | Format |
|------|---------|--------|
| Raw (Bronze) | Ingested as-is | Parquet/ORC |
| Cleaned (Silver) | Validated, deduplicated | Parquet |
| Curated (Gold) | Business-ready | Delta/Iceberg |

---

### 2.2 Data Lake Best Practices

- **Partition by date/entity** — Most queries filter by time
- **Use columnar formats** — Parquet for analytics
- **Separate hot/cold data** — Tiered storage for cost
- **Enforce schema on write** — Prevent bad data ingestion

---

## 3. Analytics Use Cases

### 3.1 Analytics Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Source     │     │   Data     │     │  Analytics  │
│  Systems    │────▶│   Lake     │────▶│  Warehouse │
│             │     │            │     │            │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

### 3.2 Analytics Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| Rolling aggregation | Last N periods | 7-day moving average |
| Cumulative | Running total | YTD revenue |
| Funnel analysis | Conversion steps | Signup → Activation → Paid |
| Cohort analysis | Group by time | Monthly retention by signup cohort |

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

---

### 4.2 Common AI/ML Data Patterns

| Pattern | Description |
|---------|-------------|
| Label encoding | Categorical to numeric |
| One-hot encoding | Binary columns for categories |
| Normalization | Scale to 0-1 |
| Missing imputation | Fill missing values |
| Time-based features | Temporal engineering |

---

### 4.3 MLOps Data Patterns

| Concern | Pattern |
|---------|---------|
| Data versioning | Dataset versioning |
| Feature consistency | Feature store |
| Data quality | Contract testing |
| Data lineage | Tracking |

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

---

### 5.2 Data Mesh Principles

| Principle | Implementation |
|-----------|----------------|
| Domain ownership | Teams own their data products |
| Self-serve platform | Infrastructure as code |
| Federated governance | Shared standards, local execution |
| Product thinking | Data as a product with users |

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