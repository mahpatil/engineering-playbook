# Data Integration Patterns

Patterns for synchronizing, streaming, and governing data across services and domains.

---

## 1. CDC (Change Data Capture)

Capture database changes in real-time and propagate them downstream.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Source DB  │    │    CDC       │    │  Target      │
│  (Postgres)  │───▶│  (Debezium)  │───▶│  (Kafka)     │
└──────────────┘    └──────────────┘    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Data Lake   │
                    │  or Warehouse│
                    └──────────────┘
```

**When to use:**
- Real-time data sync between systems
- Event sourcing from legacy databases
- Near-real-time analytics pipelines

---

## 2. Data Mesh Principles

Distribute data ownership across domains, treating data as a product.

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
| CDC | Real-time data sync | Near-real-time analytics |
| Data Mesh | Large orgs with many domains | Scalable data ownership |

