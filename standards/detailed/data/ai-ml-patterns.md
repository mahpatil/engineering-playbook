# AI/ML Data Patterns Standards

Standards for data engineering in machine learning pipelines, feature stores, and MLOps workflows.

---

## Why This Matters

Machine learning models are only as good as the data they are trained and served with. The dominant failure mode in production ML is not model architecture or design — it is data: training on features computed differently than inference receives, using stale features at serving time, training on data that leaks future information into the past, or having no mechanism to detect when the data distribution has shifted and the model's predictions have quietly degraded.

Machine Learning has unique data requirements that general-purpose data pipelines do not address:
- **Training-serving skew**: if the feature computation at training differs even slightly from serving, model quality degrades silently
- **Point-in-time correctness**: ML models must be trained on data as it existed at prediction time, not with the benefit of hindsight
- **Feature reuse**: recomputing the same features independently per team is expensive, inconsistent, and creates drift
- **Reproducibility**: you must be able to recreate any training dataset to debug model behavior or retrain

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Model Quality** | Correct, consistent features produce models that work in production as well as in evaluation |
| **Time-to-Market** | Feature reuse via a feature store means teams don't rebuild the same signals independently |
| **Reliability** | Monitoring and retraining pipelines keep models performing as data distribution shifts |
| **Compliance** | Audit trails on training data and model versions support regulatory explainability requirements |
| **Bias** | Use representative data, fair labeling, and continuous group-wise performance and fairness checks and adopt Responsible AI practices |
| **Cost** | Shared feature computation avoids duplicate processing across teams |

---

## Core Architecture: ML Data Pipeline

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Source    │     │  Feature Store  │     │  Model Training  │
│   Data      │────▶│                 │────▶│  (Offline)       │
│  (Bronze/   │     │  Offline Store  │     │                  │
│   Silver)   │     │  (historical)   │     └──────────────────┘
│             │     │                 │              │
│             │     │  Online Store   │◀─────────────┘
│             │     │  (low-latency)  │     ┌──────────────────┐
└─────────────┘     └─────────────────┘     │  Model Serving   │
                                            │  (Inference)     │
                                            └──────────────────┘
```

**Silver** which is cleaned, conformed, joined, with basic quality rules applied; is the best layer for **ML Engineering** for following reasons:
- Data quality - Silver applies cleaning, dedup, standardization, and conformance while still preserving event-level detail.
- Flexibility - you can compute many different features vs aggregated data in Gold
- Point-in-time correctness - typically doesnt exist in Gold typically as they may have future knowledge and aggregation
- Reproducibility and auditability
- Separation of concerns - Bronze is for ingestion and retention & gold for business consumption.





---

## Core Patterns

### 1. Feature Store

**What:** A centralized system that computes, stores, and serves features for both model training (offline) and model inference (online). It maintains two stores: an offline store for historical batch data used in training, and an online store for low-latency retrieval at serving time.

**Why:** Without a feature store, every team computes their own version of "user 30-day purchase count." They compute it differently, update it on different schedules, and the training pipeline uses a nightly batch while the serving pipeline uses a real-time count — producing training-serving skew that silently degrades the model. A feature store computes each feature once, consistently, and serves it to both paths.

**How:**
- Define features as code (Python or YAML using feast or alternative): the transformation logic, the data source, and the update cadence
- Offline store: columnar storage (Parquet/Delta) with time-travel support for point-in-time training dataset construction
- Online store: low-latency key-value store (Redis, DynamoDB) for < 10ms feature retrieval at inference time
- Sync offline → online on a defined schedule or via streaming (Kafka → feature pipeline → online store)
- Version features: when feature logic changes, write a new version rather than mutating in place

**Point-in-time correctness:**
When building a training dataset, features must reflect what was known at the time of the event — not the current value. A model predicting fraud at T must use the user's transaction count as it existed at T, not today's count.

```python
# Correct: point-in-time join
training_data = feature_store.get_historical_features(
    entity_df=labels_with_event_timestamps,  # includes event_timestamp per row
    features=["user_30d_spend", "user_login_count"]
    # Feature store joins each row to the feature value at event_timestamp
)
```

**Use:** Any ML system with more than 2–3 models, or any team where the same features are computed by multiple pipelines.

---

### 2. Feature Engineering Patterns

**Why:** Raw data is rarely in a form that a model can use directly. Feature engineering transforms raw signals into inputs that expose the patterns a model needs to learn. Bad feature engineering is a top contributor to poor model performance.

**What — Common Patterns:**

| Pattern | What It Does | When to Use |
|---------|-------------|-------------|
| **Temporal aggregation** | Sum/count/mean over a trailing window (7d, 30d, 90d) | Behavioral features (spend, logins, clicks) — captures recency and volume |
| **Normalization / Standardization** | Scale to [0,1] or zero mean, unit variance | Continuous features for gradient-based models (linear, neural networks) |
| **One-hot encoding** | Binary column per category value | Low-cardinality categoricals (payment method, device type) |
| **Target encoding** | Replace category with mean of target for that category | High-cardinality categoricals (postal code, merchant); risk of leakage if not done carefully |
| **Interaction features** | Multiply or combine two features | When a combination matters more than the individual signals (e.g., spend × days since last transaction) |
| **Missing imputation** | Fill nulls with mean, median, sentinel value, or learned value | Sparse features where null carries signal vs. truly missing data |
| **Lag features** | Value of a feature at T-1, T-7, T-30 | Time series models predicting future from past behavior |

**How:**
- Define feature engineering as versioned, testable code — not as ad-hoc notebook transformations
- Apply the same transformation code in training and serving — a single function called from both contexts prevents skew
- Document the business meaning of every feature: what it represents, its data source, its update cadence
- Monitor feature distributions in production — if a feature's distribution shifts significantly, the model's predictions degrade

---

### 3. Training Dataset Construction

**What:** The process of assembling a labeled dataset from features and ground-truth labels for model training.

**Why:** The training dataset determines the model's understanding of the world. A poorly constructed dataset produces a model that performs well in evaluation but fails in production. The most common failure: using future information (labels computed after the prediction time) to construct training features, creating leakage.

**How:**
- Label each training example with the event timestamp — the moment when a prediction would have been made
- Use point-in-time joins to retrieve feature values as they existed at the event timestamp (not current values)
- Define a label horizon: how far after the event timestamp does the label become known? (e.g., for fraud, 30 days to settle chargebacks)
- Version your training datasets — store the exact dataset used to train each model version. This is required for debugging and retraining.
- Test for leakage: any feature with a suspiciously high predictive correlation is a candidate for investigation

---

### 4. Model Registry and Versioning

**What:** A centralized store that tracks model versions, their training metadata, evaluation metrics, and deployment status.

**Why:** Without a model registry, you cannot answer: "which model version is in production?", "what data was it trained on?", "when was it deployed and by whom?", "what was its evaluation metric at training time?" These are basic questions for debugging a production issue or satisfying a compliance audit.

**How:**
- Every trained model artifact is registered before deployment: model version, training dataset version, hyperparameters, evaluation metrics
- Deployment records link model version to the serving environment and the deployment timestamp
- Promotion gates: a model moves from "staging" to "production" only after evaluation criteria are met and a human approves (for high-stakes decisions) or an automated comparison passes (for lower-stakes)
- Rollback: promoting the previous version must be a one-command operation

**Minimum metadata per model version:**
- Training dataset identifier and version
- Feature list and versions
- Evaluation metrics (AUC, precision, recall, RMSE — whatever is appropriate for the task)
- Training timestamp and trained-by (pipeline run ID or user)
- Deployment history

---

### 5. MLOps — Monitoring and Retraining

**What:** Ongoing operations that keep a deployed model performing correctly as the real world changes.

**Why:** Models are trained on historical data. The world changes. User behavior shifts, product changes alter feature distributions, external events create distribution shifts that the model has never seen. A model deployed in January can be silently wrong by April without any code change. Production monitoring is not optional — it is how you know when to retrain.

**How — What to Monitor:**

| Signal | What to Watch | Alert Condition |
|--------|--------------|----------------|
| **Prediction distribution** | Distribution of model output scores | Significant shift in score mean or variance |
| **Feature distribution** | Distribution of each input feature | Any feature drift beyond N standard deviations from training baseline |
| **Data quality** | Null rate, out-of-range values per feature | Null rate > training baseline or values outside training range |
| **Business outcome** | Downstream metric the model is optimizing | Revenue, conversion, or precision/recall on labels when available |
| **Label drift** | Distribution of ground-truth labels over time | Label rate shifts that would change model calibration |

**Retraining triggers:**
- Scheduled: retrain on a fixed cadence (weekly, monthly) even if no degradation is detected — keeps the model fresh
- Triggered: retrain when a monitoring threshold is breached
- Event-driven: retrain after a significant product or business change

---

## Data Quality for ML

**Why:** A data quality failure that produces a slightly wrong feature value is worse than a pipeline failure that stops the model from serving. A pipeline failure is visible. A silent bad feature degrades predictions invisibly until someone notices the business metric moving.

**How:**
- Validate feature values on ingest: range checks, null rate checks, type checks — fail the pipeline if thresholds are breached
- Test for feature drift weekly: compare the current distribution of each feature against its training-time distribution
- Test for label rate stability: if the positive label rate changes significantly, the model's calibration is off
- Use data contracts (schemas with quality assertions) between data producers and the feature store

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Training-serving skew | Features computed differently at training and serving; silent model degradation | Single feature computation function called from both training and serving |
| Future leakage in training data | Model "learns" from information it could not have had at prediction time; overstates real-world performance | Point-in-time joins with explicit event timestamps |
| No training dataset versioning | Cannot reproduce a model, debug failure, or retrain from the same baseline | Store exact training dataset version alongside every model version |
| No production monitoring | Silent model degradation goes undetected until business impact is visible | Monitor prediction distribution, feature drift, and business outcomes |
| Retraining without evaluation | A retrained model that performs worse gets promoted automatically | Evaluation gate before promotion: new model must meet minimum metric thresholds |
| Feature logic in notebook, not in code | Feature engineering cannot be tested, versioned, or reused | Feature transformations as versioned Python functions or dbt transformations |
| Treating model deployment like application deployment | Model rollback requires different tooling and often immediate action | Model registry with one-command rollback and automated health checks post-deployment |
