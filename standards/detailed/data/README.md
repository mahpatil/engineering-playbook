# Data Architecture Standards

Standards for designing, building, and operating data systems in a cloud-native microservices environment.

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Team Autonomy** | Services own their data; teams ship without coordinating schema changes with other teams |
| **Independent Scalability** | Scale storage and databases per service based on actual demand, not the peak of the largest tenant |
| **Fault Isolation** | A database failure in one service is contained — it does not cascade across the system |
| **Analytics Separation** | Analytical workloads run against a data lake, not production databases — production stays fast |
| **Data Quality** | Explicit ownership, contracts, and validation prevent the "nobody owns this data" failure mode |
| **AI Readiness** | A governed data foundation (lake zones, feature stores) makes ML and analytics initiatives cheaper to build |
| **Compliance & Multi-Tenancy** | Tenant isolation and audit-friendly data designs reduce breach risk and satisfy regulatory requirements |

---

## Core Principles

### 1. Database per Service
Each service owns exactly one data store. No other service connects to it directly — cross-service data access goes through APIs or events, never shared schemas. This is the foundation of team autonomy and fault isolation. See [Data Architecture](./data-architecture.md).

### 2. Sagas, Not Distributed Transactions
Multi-service operations use the Saga pattern — a sequence of local transactions with compensating rollbacks — instead of two-phase commit, which is theoretically correct but operationally fragile. Designs assume eventual consistency across service boundaries. See [Data Architecture](./data-architecture.md).

### 3. CQRS Where Reads and Writes Diverge
When query patterns differ significantly from the write model, separate the write model (commands) from the read model (projections). Apply only when genuinely justified — never for simple CRUD. See [Data Architecture](./data-architecture.md).

### 4. Operational vs Analytical Separation
Production databases serve only live, latency-sensitive queries. Analytical workloads run against a dedicated data lake or warehouse, synced via CDC or event publishing — never by querying production. See [Data Architecture](./data-architecture.md) and [Data Lake](./data-lake.md).

### 5. Choose the Right Database for the Job
Relational and NoSQL databases are evaluated against the workload, consistency needs, and access patterns — polyglot persistence is the norm, not an afterthought. See [Database Type Selection](./database-type.md).

### 6. Governed Data Lake (Bronze / Silver / Gold)
Raw, cleaned, and curated data live in distinct lake zones with defined ingestion, storage-format, and data-quality standards, so downstream consumers trust the data. See [Data Lake](./data-lake.md).

### 7. Metrics Built on Consistent Definitions
Analytics (rolling aggregation, cumulative, funnel, cohort) are only as good as their measure definitions — metric consistency standards prevent "our numbers don't match" across teams. See [Analytics Patterns](./analytics-patterns.md).

### 8. Data as an Enabler for AI/ML
Feature stores, point-in-time correctness, and model registries make ML reproducible and production-grade, built on the same governed data foundation. See [AI/ML Data Patterns](./ai-ml-patterns.md).

### 9. Tenant Isolation by Design
Multi-tenant SaaS enforces isolation at the data layer (schema-per-tenant, database-per-tenant, or shared-schema with row-level guards), not just at the auth layer — a tenant must never see another tenant's data. See [Azure Multi-Tenant Design](./azure-multi-tenant-data-design-patterns.md).

---

## Documents

| Standard | What It Covers |
|----------|---------------|
| [Data Architecture](./data-architecture.md) | Core patterns: database per service, Saga, CQRS, operational vs analytical separation |
| [Database Type Selection](./database-type.md) | Relational vs NoSQL decision guide; when to use each NoSQL type; polyglot persistence rules |
| [Data Lake](./data-lake.md) | Bronze/Silver/Gold zones; ingestion patterns; storage formats; data quality standards |
| [Analytics Patterns](./analytics-patterns.md) | Rolling aggregation, cumulative, funnel, cohort analysis; metric consistency standards |
| [AI/ML Data Patterns](./ai-ml-patterns.md) | Feature store, point-in-time correctness, model registry, MLOps monitoring |
| [Azure Multi-Tenant Design](./azure-multi-tenant-data-design-patterns.md) | Tenant isolation patterns for Azure SQL and Cosmos DB; shared schema vs database per tenant |

---

## Where to Start

**New to the data standards?** Start with [Data Architecture](./data-architecture.md) — it explains the foundational principles (database per service, Saga, CQRS) that underpin everything else.

**Choosing a database?** Go to [Database Type Selection](./database-type.md).

**Building analytics or reporting?** Go to [Analytics Patterns](./analytics-patterns.md) and [Data Lake](./data-lake.md).

**Building ML systems?** Go to [AI/ML Data Patterns](./ai-ml-patterns.md).

**Building multi-tenant SaaS on Azure?** Go to [Azure Multi-Tenant Design](./azure-multi-tenant-data-design-patterns.md).

---

## Related Standards

- [Integration Patterns](../integration/data-integration-patterns.md) — CDC, Data Mesh, event-driven data sync
