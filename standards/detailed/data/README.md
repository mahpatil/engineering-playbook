# Data Architecture Standards

Standards for designing, building, and operating data systems in a cloud-native microservices environment.

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
