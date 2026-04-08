# Multi-Tenant Data Design Patterns on Azure

## Overview
This document summarizes recommended data design patterns for building a multi-tenant SaaS platform using Azure SQL and Cosmos DB. It focuses on schema design, scalability, pros/cons, and when to use each pattern.

---

# Azure SQL Database (Relational / Financial Core)

## 1. Shared Schema (Tenant ID)

### Schema Design
```sql
orders (
  order_id,
  tenant_id,
  customer_id,
  amount,
  status
)
```

### How it works
- All tenants share the same tables
- `tenant_id` separates data
- Row-Level Security (RLS) enforces isolation

### Scale
- 10K–100K+ tenants
- 1K–10K+ transactions/sec per DB (higher with Hyperscale)
- TBs of structured data

### Pros
- Simple and cost efficient
- Easy to scale
- Works well with microservices

### Cons
- Requires strict security controls
- Harder per-tenant backup/restore
- May not satisfy strict regulatory isolation

---

## 2. Schema per Tenant

### Schema Design
```sql
tenant_a.orders
tenant_b.orders
```

### How it works
- Each tenant has its own schema
- Same structure repeated per tenant

### Scale
- 100–5,000 tenants (practical range)

### Pros
- Better isolation
- Easier tenant-level operations
- Cleaner logical separation

### Cons
- Increased operational complexity
- Harder to manage at scale
- Deployment overhead

---

## 3. Database per Tenant

### Schema Design
- Separate database per tenant

### Scale
- 100–10,000+ tenants (via elastic pools)

### Pros
- Strongest isolation
- Independent scaling
- Easier migration/offboarding

### Cons
- Higher cost
- More infrastructure management

---

## 3. Schema per Microservice (Recommended Default)

### Design
- Each microservice owns its own schema within a shared database

```sql
CREATE SCHEMA orders;
CREATE SCHEMA payments;
CREATE SCHEMA customers;
```

### Example
```sql
orders.orders
payments.transactions
customers.profiles
```

### How it works
- Logical isolation per microservice
- Each service manages its own schema and tables
- No cross-schema writes (enforced via service boundaries)

### Scale
- 50–200+ microservices per database (grouped via elastic pools)

### Pros
- Clear ownership boundaries
- Avoids cross-service coupling
- Easier independent deployments
- Works well with shared infrastructure

### Cons
- Requires governance to avoid schema sprawl
- Cross-service queries become harder (by design)

---

## Recommended Pattern (SQL)
- Default: Shared schema + tenant_id + Schema per microservice
- Premium tenants: Schema or DB per tenant
- Use elastic pools for cost efficiency

---

# Cosmos DB (High Scale / API Layer)

## 1. Shared Container (Partition by Tenant)

### Schema Design
```json
{
  "id": "order1",
  "tenantId": "tenantA",
  "customerId": "123",
  "amount": 100
}
```

### How it works
- Single container
- Partition key = `/tenantId`

### Scale
- Millions of tenants
- Millions of requests/sec
- Virtually unlimited storage

### Pros
- Massive scale
- Cost efficient
- Simple architecture
- Multi-region ready

### Cons
- Requires careful partition design
- Risk of hot partitions
- Limited relational querying

---

## 2. Container per Microservice

### Design
Each microservice owns a container
```
orders-container
customers-container
```

### How it works
- Each service owns a container
- Partitioned by tenant

### Scale
- Hundreds of containers per account

### Pros
- Clear ownership per service
- Independent scaling
- Good microservice alignment

### Cons
- Slightly higher cost
- Requires partition discipline

---

## 3. Account per Domain

### Design
```
Account A → Core APIs
Account B → Analytics / Events
```

### Scale
- Millions of RU/s per account
- Global distribution

### Pros
- Strong isolation (performance + security)
- Region/compliance separation

### Cons
- Higher cost
- More operational overhead

---

## Recommended Pattern (Cosmos)
- Default: Shared account + container per service
- Partition key: tenantId
- Split accounts only for region, compliance, or extreme scale

---

# Azure SQL vs Cosmos DB Summary

| Feature | Azure SQL | Cosmos DB |
|--------|----------|----------|
| Best for | Financial transactions | High-scale APIs |
| Data model | Relational | NoSQL (JSON) |
| Multi-tenancy | tenant_id / schema / DB | Partition key |
| Scale | 1K–10K TPS per DB | Millions RPS |
| Storage | TBs | Practically unlimited |
| Consistency | Strong (ACID) | Tunable |
| Cost model | Compute-based | Throughput (RU/s) |

---

# Microservice Schema Design Patterns

## 1. Schema per Microservice (Recommended Default)

### Design
- Each microservice owns its own schema within a shared database

```sql
CREATE SCHEMA orders;
CREATE SCHEMA payments;
CREATE SCHEMA customers;
```

### Example
```sql
orders.orders
payments.transactions
customers.profiles
```

### How it works
- Logical isolation per microservice
- Each service manages its own schema and tables
- No cross-schema writes (enforced via service boundaries)

### Scale
- 50–200+ microservices per database (grouped via elastic pools)

### Pros
- Clear ownership boundaries
- Avoids cross-service coupling
- Easier independent deployments
- Works well with shared infrastructure

### Cons
- Requires governance to avoid schema sprawl
- Cross-service queries become harder (by design)

---

## 2. Database per Microservice (Selective Use)

### Design
- Each microservice has its own database

### Scale
- 10–100+ databases (grouped in elastic pools)

### Pros
- Strong isolation per service
- Independent scaling
- Easier lifecycle management

### Cons
- Higher cost
- Operational overhead increases significantly

---

# Final Architecture Recommendation

## Core System (System of Record)
- Azure SQL
- Pattern: Shared schema + tenant_id

## Scale Layer (APIs / Events)
- Cosmos DB
- Pattern: Container per service + tenantId partition

---

# Bottom Line

- Use Azure SQL for correctness, compliance, and financial data
- Use Cosmos DB for scale, performance, and global distribution

This combination supports:
- 50+ microservices
- Millions of tenants
- Billions of transactions and events
