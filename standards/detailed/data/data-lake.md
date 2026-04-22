# Data Lake Architecture

Centralized repository storing raw data at any scale, organized in zones for progressive refinement.

---

## 1. Data Lake Overview

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

| Zone | Purpose | Format |
|------|---------|--------|
| Raw (Bronze) | Ingested as-is | Parquet/ORC |
| Cleaned (Silver) | Validated, deduplicated | Parquet |
| Curated (Gold) | Business-ready | Delta/Iceberg |

---

## 2. Analytics Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Source     │     │   Data     │     │  Analytics  │
│  Systems    │────▶│   Lake     │────▶│  Warehouse │
│             │     │            │     │            │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## 3. Best Practices

- **Partition by date/entity** — Most queries filter by time
- **Use columnar formats** — Parquet for analytics
- **Separate hot/cold data** — Tiered storage for cost
- **Enforce schema on write** — Prevent bad data ingestion
