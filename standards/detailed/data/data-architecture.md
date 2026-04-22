# Data Architecture Standards

Foundational principles and patterns for building scalable, maintainable data systems in a microservices environment.

---

## Why This Matters

Data architecture decisions have the longest blast radius of any technical choice. A monolithic database shared across services feels convenient on day one and becomes the central point of failure and the biggest obstacle to team autonomy by year two. Cross-service queries turn into political negotiations. Schema changes block multiple teams. A single slow query degrades every service using the same database.

The patterns here encode hard-won lessons about what breaks at scale: shared databases, synchronous distributed transactions, and analytics workloads mixed with operational traffic. Each pattern solves a specific problem that emerges as systems and teams grow.

---

## How This Documentation Is Organized

| Topic | Document |
|-------|----------|
| Database type selection (relational vs NoSQL) | [database-type.md](./database-type.md) |
| Data lake architecture (Bronze/Silver/Gold) | [data-lake.md](./data-lake.md) |
| Analytics patterns (cohort, funnel, rolling, cumulative) | [analytics-patterns.md](./analytics-patterns.md) |
| AI/ML data patterns (feature store, MLOps) | [ai-ml-patterns.md](./ai-ml-patterns.md) |
| Multi-tenant data design on Azure | [azure-multi-tenant-data-design-patterns.md](./azure-multi-tenant-data-design-patterns.md) |
| Integration patterns (CDC, Data Mesh) | [../integration/data-integration-patterns.md](../integration/data-integration-patterns.md) |

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Team Autonomy** | Services own their data; teams ship without coordinating schema changes with others |
| **Independent Scalability** | Scale data storage per service based on actual demand, not the peak of the largest tenant |
| **Fault Isolation** | A database failure in one service does not cascade across the system |
| **Analytics Separation** | Analytical queries run against a data lake, not production databases — keeping production fast |
| **Data Quality** | Explicit ownership and contracts prevent the "nobody owns this data" failure mode |

---

## Core Principles

### 1. Database per Service

**What:** Each microservice owns exactly one data store. No other service connects to it directly. Cross-service data access goes through the service API.

**Why:** A shared database couples services at the schema layer. A column rename in one table breaks every service that queries it. A schema migration requires coordination across teams. The database becomes the de facto integration layer, and with it comes the worst properties of a monolith — shared state, shared failure, shared deployment coupling — without its benefits.

**What this means:**
- No shared connection strings between services
- No cross-service SQL joins at query time
- Data needed by another service is exposed via API or replicated via events
- Schema migrations are owned entirely by the service team; no approval chain required

**Example:**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Orders     │     │  Customers  │     │  Payments   │
│  Service    │     │  Service    │     │  Service    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
   ┌───┴───┐           ┌───┴───┐           ┌───┴───┐
   │Orders │           │Cust-  │           │Pay-   │
   │ DB    │           │omers  │           │ments  │
   │       │           │ DB    │           │ DB    │
   └───────┘           └───────┘           └───────┘
```

**When to use:** Always, for services that will be developed by separate teams or need to scale independently.

**Avoid when:** Two logical services always deploy together, share the same team, and have no independent scaling needs — consider whether they are truly separate services.

---

### 2. Saga Pattern for Distributed Transactions

**What:** Coordinate a multi-step business operation across services using a sequence of local transactions, where each step publishes an event that triggers the next, and failures trigger compensating transactions to undo completed steps.

**Why:** Distributed transactions (two-phase commit) are theoretically correct but operationally fragile — they require all participants to be available simultaneously, hold locks across services during coordination, and fail in complex ways. Sagas trade strict consistency for availability: each service commits locally and publishes an event; if a later step fails, compensating events undo prior steps.

**Two styles:**

| Style | How | When |
|-------|-----|------|
| **Choreography** | Each service listens for events and decides its own next step | Simpler flows with < 4 steps; no central coordinator needed |
| **Orchestration** | A saga orchestrator sends commands to each service and handles failures | Complex flows with branching logic; easier to observe and debug |

**What this means:**
- Each local transaction must be idempotent — safe to retry if a message is redelivered
- Compensating transactions undo the effect of a completed step (e.g., refund a charge, release reserved inventory)
- Saga state is persisted — if the orchestrator crashes mid-saga, it resumes from the last checkpoint
- Eventual consistency is the result: the system converges to a correct state, but there are windows of inconsistency

**Example — Order Placement:**

```
Order Service          Payment Service        Inventory Service
     │                      │                      │
     │── OrderPlaced ───────▶│                      │
     │                      │── PaymentProcessed ──▶│
     │                      │                      │── InventoryReserved
     │                      │                      │
     │  ← − − − − − − − − −  FAILURE: Payment Declined − − − − − − − −
     │                      │
     │── OrderCancelled ◀───│   (compensating transaction)
```

**When to use:** Any business operation that spans more than one service and requires all-or-nothing semantics.

**Avoid when:** The operation can be decomposed so each service handles its own transaction independently, without requiring cross-service rollback.

---

### 3. CQRS — Command Query Responsibility Segregation

**What:** Separate the write model (commands that change state) from the read model (queries that return data). Each is optimized independently.

**Why:** A single data model that must serve both high-throughput writes and complex analytical reads ends up poorly optimized for both. The write model needs normalized data and strong consistency. The read model needs denormalized, pre-joined data optimized for the query patterns of its consumers. Forcing one model to serve both creates contention, complex queries, and schema compromises.

**What this means:**
- Writes go to the command model (normalized relational store, event log)
- The command model publishes events when state changes
- A projection builds and maintains the read model from those events (materialized view, search index, reporting database)
- Reads are served from the read model — the query is fast because the data is already shaped for it
- The read model may be eventually consistent with the write model

```
 Commands (writes)              Queries (reads)
──────────▶                    ◀──────────────
    │                               │
    ▼                               ▼
┌─────────┐   Event/Stream   ┌──────────────┐
│  Write  │─────────────────▶│  Read Model  │
│  Model  │                  │  (OLAP /     │
│  (OLTP) │                  │   Projection)│
└─────────┘                  └──────────────┘
```

**When to use:**
- Read and write volumes differ significantly (high-write service with complex reporting needs)
- Query patterns require data shapes that differ significantly from the write model
- Multiple consumers need different views of the same data (order service needs order history; analytics needs order aggregates; search needs indexed titles)

**Avoid when:** The service has simple CRUD operations with similar read/write patterns — CQRS adds complexity that is not justified.

---

### 4. Operational Data vs Analytical Data

**What:** Keep operational data (transactional, live, latency-sensitive) separate from analytical data (historical, aggregated, batch-processed).

**Why:** Analytics queries scan millions of rows. Operational queries hit single rows by primary key. Running both on the same database means a full-table scan for a monthly report competes with a customer checkout request for the same I/O bandwidth. One will lose. In practice, both lose.

**What this means:**
- Production databases serve only operational, latency-sensitive queries
- Analytical workloads run against the data lake or a dedicated warehouse (Synapse, BigQuery, Databricks)
- Data flows from operational → lake via CDC (Change Data Capture) or event publishing — not via direct queries against production
- Analysts are given read access to the data lake, never to production databases

---

## Summary: When to Use Each Pattern

| Pattern | When to Use | Key Benefit |
|---------|-------------|-------------|
| **Database per Service** | Always, for independently deployed services | Loose coupling; teams own their data |
| **Saga** | Multi-service operations requiring all-or-nothing semantics | Distributed consistency without two-phase commit |
| **CQRS** | Different read/write scaling or query shape requirements | Optimized read and write paths independently |
| **Data Lake** | Analytics at scale; historical queries; ML training data | Operational databases stay fast; analytics scales cheaply |
| **Feature Store** | ML systems with shared features across models | Eliminates training-serving skew; enables feature reuse |
| **CDC** | Real-time replication from operational DB to lake or cache | Zero impact on source system; near-real-time sync |

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Shared database between services | Schema coupling, deployment coupling, shared failure blast radius | Database per service |
| Synchronous distributed transactions (2PC) | Locks across services; failure modes cascade; availability bottleneck | Saga pattern with compensating transactions |
| Analytical queries against production databases | Analytics scans compete with live user traffic; both degrade | Route analytics to data lake; use CDC to sync |
| CQRS for simple CRUD services | Unnecessary complexity; eventual consistency bugs in low-traffic systems | Apply CQRS only when read/write patterns genuinely diverge |
| No event publishing on state changes | Other services cannot react without polling; tight temporal coupling | Publish domain events on every state change |
