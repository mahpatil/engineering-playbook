# AI/ML Data Patterns

Data engineering patterns for machine learning pipelines, feature stores, and MLOps workflows.

---

## 1. ML Data Pipeline

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

## 2. Common Feature Engineering Patterns

| Pattern | Description |
|---------|-------------|
| Label encoding | Categorical to numeric |
| One-hot encoding | Binary columns for categories |
| Normalization | Scale to 0-1 |
| Missing imputation | Fill missing values |
| Time-based features | Temporal engineering |

---

## 3. MLOps Data Patterns

| Concern | Pattern |
|---------|---------|
| Data versioning | Dataset versioning |
| Feature consistency | Feature store |
| Data quality | Contract testing |
| Data lineage | Tracking |
