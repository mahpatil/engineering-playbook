# Data Architecture

Foundational data architecture patterns for building scalable systems.

---

## Sections

| Topic | File |
|-------|------|
| Database Design in Microservices | [This document, Section 1](#1-database-design-in-microservices) |
| Data Lake Architecture | [data-lake.md](./data-lake.md) |
| Analytics Patterns | [analytics-patterns.md](./analytics-patterns.md) |
| AI/ML Data Patterns | [ai-ml-patterns.md](./ai-ml-patterns.md) |
| Integration Patterns (CDC, Data Mesh) | [integration/data-integration-patterns.md](../integration/data-integration-patterns.md) |

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

## Summary

| Pattern | When to Use | Key Benefit |
|---------|-------------|-------------|
| Database per Service | Microservices with independent data | Loose coupling |
| CQRS | Different read/write patterns | Performance optimization |
| Data Lake | Analytics at scale | [See data-lake.md](./data-lake.md) |
| Feature Store | ML training/inference | [See ai-ml-patterns.md](./ai-ml-patterns.md) |
| CDC | Real-time data sync | [See data-integration-patterns.md](../integration/data-integration-patterns.md) |
