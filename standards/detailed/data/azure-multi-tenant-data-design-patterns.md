# Multi-Tenant Data Design Patterns on Azure

Standards for designing data isolation, scalability, and access control in multi-tenant SaaS systems on Azure.

---

## Why This Matters

Multi-tenancy is one of the most consequential architectural decisions in a SaaS product. The wrong isolation model leaks data between tenants (a compliance and trust catastrophe), creates hot-tenant performance problems that degrade all customers, or generates infrastructure costs that make low-tier pricing economically unviable.

Getting this right requires choosing the isolation model that matches your tenants' regulatory requirements, your expected scale, and your operational capacity — and applying it consistently across every data store in the system.

The failure modes are expensive: migrating from shared-schema to per-tenant database at 10,000 tenants requires data migration at scale; a missing `WHERE tenant_id = ?` predicate exposes all tenants' data; a single enterprise tenant consuming 80% of shared throughput degrades everyone else.

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Data Isolation** | No tenant sees another tenant's data — a legal and trust requirement for every SaaS product |
| **Performance Isolation** | A noisy tenant does not degrade service quality for others |
| **Regulatory Compliance** | Enterprise and regulated customers require demonstrable data separation |
| **Cost Efficiency** | Shared infrastructure reduces per-tenant cost for lower-tier customers |
| **Operational Scalability** | The isolation model must work at 10, 1,000, and 100,000 tenants without a full rewrite |

---

## Azure SQL — Relational Data (System of Record)

Azure SQL handles financial transactions, operational records, and any data requiring ACID guarantees and relational integrity.

### Pattern 1: Shared Schema with Tenant ID

**What:** All tenants share the same tables. A `tenant_id` column separates their data. Row-Level Security (RLS) enforces that queries only return rows belonging to the calling tenant.

**Why:** This is the most cost-efficient model for high-tenant-count SaaS. Infrastructure is shared, schema changes deploy once, and operations (backup, patching, monitoring) scale linearly rather than per-tenant. It is the right default for the majority of tenants.

**How:**
- Add `tenant_id` to every table that holds tenant-scoped data
- Implement Row-Level Security policies that filter on the application's tenant context variable:

```sql
-- Security policy filters all reads and writes by tenant_id
CREATE SECURITY POLICY tenant_isolation
ADD FILTER PREDICATE dbo.fn_tenant_check(tenant_id) ON dbo.orders,
ADD BLOCK PREDICATE dbo.fn_tenant_check(tenant_id) ON dbo.orders;
```

- Set the tenant context at connection time before executing queries:

```sql
EXEC sp_set_session_context 'tenant_id', @tenantId;
```

- Use Elastic Pools to share compute across tenants while maintaining per-tenant resource limits
- Test RLS policies in CI — a failing predicate silently drops rows rather than returning an error

**Scale:** 10,000–100,000+ tenants | 1,000–10,000+ TPS per database (higher with Hyperscale)

**Use for:** Default tier tenants; high-tenant-count SaaS; workloads where operational simplicity is the priority.

**When to move away:** Tenant requires contractual proof of data separation; regulatory obligation mandates physical isolation; tenant is large enough to noisy-neighbor others.

---

### Pattern 2: Schema per Tenant

**What:** Each tenant gets their own SQL schema within a shared database. Tables are physically separate per tenant, but compute is shared.

**Why:** Provides logical isolation stronger than shared-schema without the cost of a full database per tenant. Simplifies tenant-level operations — backup a tenant's schema, run tenant-specific migrations, or offboard a tenant by dropping their schema.

**How:**
- Provision a schema per tenant on onboarding:

```sql
CREATE SCHEMA tenant_a;
CREATE TABLE tenant_a.orders (...);
CREATE TABLE tenant_a.payments (...);
```

- Application routes queries to the correct schema based on tenant context
- Apply schema-level permissions to restrict cross-tenant access at the database layer
- Automate schema provisioning and migration via tooling (not manual DDL)

**Scale:** 100–5,000 tenants per database

**Use for:** Mid-tier customers requiring audit-demonstrable isolation; tenants with custom schema extensions; regulatory requirements that stop short of requiring separate databases.

**When to move away:** Tenant count exceeds 5,000 (schema metadata overhead becomes measurable); tenant requires a dedicated SLA.

---

### Pattern 3: Database per Tenant

**What:** Each tenant has a completely separate Azure SQL database. Compute, storage, and connections are fully isolated.

**Why:** Maximum isolation. A tenant can be migrated to a different region, backed up and restored independently, or offboarded by deleting their database — without touching any other tenant. Enterprise customers and regulated industries (banking, healthcare) often require this as a contractual or compliance obligation.

**How:**
- Group tenant databases in Azure Elastic Pools for cost efficiency — pools share compute while databases remain isolated
- Use a tenant registry (a central database or configuration store) that maps `tenant_id` → `connection string`
- Route application traffic through a connection broker that resolves the correct database per request
- Automate provisioning via Terraform — new tenant databases must be created from a template, not manually

**Scale:** 100–10,000+ databases via elastic pools

**Use for:** Enterprise tier; regulatory mandates for physical separation; tenants with strict performance SLAs.

**Cost note:** This model has the highest per-tenant cost. Offset with Elastic Pools and size pools to tenant workload characteristics.

---

### Schema per Microservice (Cross-Cutting Pattern)

**What:** Within any tenant isolation model above, each microservice owns its own schema. No service writes to another service's schema.

**Why:** Service ownership of data is non-negotiable in a microservices architecture. Without schema-level boundaries, a service change by one team can silently break another service's queries. Schema per microservice enforces the contract at the database layer.

**How:**
```sql
CREATE SCHEMA orders;
CREATE SCHEMA payments;
CREATE SCHEMA customers;

-- Each service only has permission on its own schema
GRANT SELECT, INSERT, UPDATE ON SCHEMA::orders TO orders_service;
GRANT SELECT, INSERT, UPDATE ON SCHEMA::payments TO payments_service;
```

- Services must not query another service's schema directly
- Cross-service data access goes through the service API or an event stream
- Database migrations are owned and run by the service team for their schema only

---

### SQL Recommendation

| Tenant Tier | Pattern | Rationale |
|-------------|---------|-----------|
| Default / Free / SMB | Shared schema + tenant_id + RLS | Cost-efficient; operations scale without per-tenant overhead |
| Professional | Schema per tenant | Demonstrable logical isolation; supports tenant-level operations |
| Enterprise | Database per tenant (Elastic Pool) | Physical isolation; compliance-ready; independent SLA |

---

## Cosmos DB — High-Scale API Layer

Cosmos DB handles API-facing data that requires sub-10ms latency, global distribution, and millions of requests per second — product catalogs, event streams, user activity, and operational API data.

### Pattern 1: Shared Container (Partition by Tenant)

**What:** All tenants share a single Cosmos DB container. The partition key is `tenantId`, which physically co-locates each tenant's data on the same storage partition.

**Why:** This is the simplest and most cost-efficient Cosmos DB architecture. A single container with tens of millions of documents is trivial for Cosmos DB. Partitioning by `tenantId` gives each tenant a logical partition with its own throughput allocation.

**How:**
- Set partition key to `/tenantId` on container creation — this cannot be changed later
- Every document must include `tenantId` and all queries must include it as a filter:

```json
{
  "id": "order-001",
  "tenantId": "tenant-abc",
  "customerId": "cust-123",
  "amount": 9900,
  "status": "placed"
}
```

- Enforce `tenantId` filter in application middleware — not per-query. A missing filter exposes all tenants' data.
- Monitor per-partition RU consumption. A tenant generating > 20% of total RUs is a hot partition candidate — consider dedicated throughput for that tenant.

**Scale:** Millions of tenants | Millions of requests/sec | Virtually unlimited storage

**Use for:** Default tier tenants; high-cardinality entity types; any data where scale and cost efficiency matter more than per-tenant operational isolation.

---

### Pattern 2: Container per Microservice

**What:** Each microservice owns its own Cosmos DB container within a shared account. Partitioned by `tenantId`.

**Why:** Microservice data ownership applies equally to Cosmos DB. Separate containers enforce that one service cannot read or write another service's data at the database layer. They also enable independent scaling — a high-traffic orders container gets more throughput without increasing cost for a low-traffic customers container.

**How:**
```
orders-container      → owned by order-service
customers-container   → owned by customer-service
events-container      → owned by event-service
```

- Each container uses `/tenantId` as the partition key
- Each service has a distinct connection key with access scoped to its container only
- Index policies are configured per container — index only the fields queried by the owning service

**Scale:** Hundreds of containers per Cosmos DB account

**Use for:** Any microservices-based system using Cosmos DB. This should be the default.

---

### Pattern 3: Account per Domain

**What:** Separate Cosmos DB accounts for distinct domains (e.g., core operational APIs in one account, analytics and event data in another).

**Why:** Account-level isolation provides the strongest separation — different region configurations, different backup policies, different compliance boundaries, and independent scaling limits. Some enterprises require data residency in specific regions; account-level separation is the mechanism.

**How:**
```
Account A: core-operations   → orders, customers, payments
Account B: analytics-events  → event streams, audit logs, reporting data
```

- Use private endpoints for each account — no public internet access
- Separate managed identities per account for access control
- Consider this when: regulatory data residency requirements differ by domain, or domains have meaningfully different global distribution requirements

**Scale:** Millions of RU/s per account; global distribution per account

**Use for:** Enterprise compliance scenarios; strict data residency requirements; domains with very different availability and consistency profiles.

---

### Cosmos DB Recommendation

| Use Case | Pattern |
|----------|---------|
| Default / all tenants | Shared account + container per microservice + `/tenantId` partition key |
| Enterprise isolation | Separate container with dedicated throughput per tenant |
| Domain-level compliance / residency | Account per domain |

---

## Azure SQL vs Cosmos DB — Decision Guide

| Factor | Azure SQL | Cosmos DB |
|--------|-----------|-----------|
| **Best for** | Financial data, compliance records, relational reporting | High-scale APIs, event streams, global distribution |
| **Data model** | Relational — tables, joins, foreign keys | Document — JSON, no joins |
| **Consistency** | Strong ACID | Tunable: strong, bounded staleness, eventual |
| **Scale ceiling** | ~10K TPS per database (Hyperscale for more) | Millions of RPS per account |
| **Multi-tenancy** | `tenant_id` column + RLS / Schema / Database | Partition key = `tenantId` |
| **Cost model** | Compute (vCores) + storage | Throughput (RU/s) + storage |
| **Query flexibility** | Full SQL — ad-hoc joins, aggregations | Partition-key-scoped SQL — limited cross-partition |
| **Operational model** | Elastic Pools for multi-tenant cost efficiency | Shared throughput or provisioned per container |

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Missing `tenant_id` filter in application queries | Cross-tenant data exposure | Enforce tenant filter at middleware layer, not per-query |
| No Row-Level Security on shared schema | A bug in application code exposes all tenant data | RLS at database layer as defense-in-depth |
| Cosmos DB without `tenantId` in partition key | All tenants on one partition; hot partition; cannot scale per tenant | Always partition by `tenantId` for multi-tenant containers |
| Shared schema for enterprise/regulated tenants | Cannot satisfy compliance or contractual isolation requirements | Schema or database per tenant for regulated customers |
| Manual database provisioning per tenant | Operational overhead grows linearly; provisioning mistakes | Terraform-automated provisioning from a template |
| Cross-service schema access in SQL | Service coupling at the database layer; blocks independent deployments | Schema-level permissions; each service owns exactly one schema |
| Cosmos DB without per-partition RU monitoring | Hot tenants degrade others silently | Alert on per-partition RU consumption above threshold |
