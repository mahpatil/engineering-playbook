# Analytics Patterns Standards

Standards for designing analytical queries, reporting pipelines, and business intelligence workloads.

---

## Why This Matters

Analytics is where data informs decisions. The patterns here are not academic — they are the difference between a finance team trusting their dashboard and maintaining a parallel spreadsheet, or a product team understanding whether a feature actually improved activation or just coincided with a seasonal uptick.

Getting analytics patterns wrong manifests as: queries that take 10 minutes when they should take 10 seconds, reports that disagree with each other because they compute the same metric differently, cohort analyses that mix up calendar effects with behavioral effects, and funnels that show misleading conversion rates because the step ordering was wrong.

Each pattern in this document exists because a class of business question requires a specific computational approach. Using the wrong approach produces wrong answers — not obviously wrong, just subtly wrong in ways that only surface when the business acts on them.

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Decision Quality** | Correct analytical patterns produce trustworthy numbers that stakeholders act on |
| **Query Performance** | Right pattern + right aggregation avoids full scans and expensive re-computation |
| **Metric Consistency** | Standardized patterns ensure the same question gets the same answer across teams |
| **Analyst Productivity** | Well-structured Gold tables let analysts answer questions without writing complex joins |
| **Reproducibility** | Defined computation logic means auditors and engineers can verify any number |

---

## Core Patterns

### 1. Rolling Aggregation

**What:** Compute a metric over a sliding window of time (last N days/weeks/months), moving forward as time advances.

**Why:** Point-in-time metrics are noisy — a single bad day distorts the picture. Rolling aggregations smooth short-term variance so trends are visible. A 7-day moving average of daily active users reveals whether growth is real or driven by a single viral event.

**How:**
- Use a window function over an ordered partition: `AVG(metric) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)`
- Pre-materialize rolling windows in Gold tables for dashboard performance — don't compute them at query time for large datasets
- Define window size based on noise characteristics of the metric: high-variance metrics need longer windows; operational metrics (error rate) need shorter windows for alerting

**Example:**
```sql
SELECT
  date,
  revenue,
  AVG(revenue) OVER (
    ORDER BY date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS revenue_7d_avg
FROM daily_revenue
ORDER BY date;
```

**Use for:** Trend monitoring, anomaly detection, smoothed KPI dashboards, moving average forecasting baselines.

---

### 2. Cumulative (Running Total)

**What:** Accumulate a metric from a fixed start point to the current row, producing a running sum.

**Why:** Financial reporting, progress-toward-goal, and subscription metrics require understanding where you are relative to where you started. "How much have we billed this quarter?" is a cumulative question. Point-in-time daily revenue does not answer it.

**How:**
- Use `SUM(metric) OVER (PARTITION BY period ORDER BY date ROWS UNBOUNDED PRECEDING)`
- Reset the accumulation at meaningful business boundaries: fiscal year start, cohort entry date, campaign start
- For "progress to target" use cases, join against a target table and compute percentage completion as a derived column

**Example:**
```sql
SELECT
  date,
  revenue,
  SUM(revenue) OVER (
    PARTITION BY fiscal_year
    ORDER BY date
    ROWS UNBOUNDED PRECEDING
  ) AS ytd_revenue
FROM daily_revenue;
```

**Use for:** Year-to-date revenue, cumulative installs, progress-to-quota, running subscription count.

---

### 3. Funnel Analysis

**What:** Track users or transactions through a defined sequence of steps and measure conversion at each step.

**Why:** Product onboarding, checkout flows, and sales pipelines are sequential processes. A 20% drop between step 2 and step 3 is invisible if you only look at start and end — you cannot fix what you cannot see. Funnel analysis surfaces where volume is lost.

**Why this is harder than it looks:** Users do not follow steps in strict order. A naive count at each step double-counts users who repeated a step, or misses users who completed later steps before earlier ones (e.g., paid before verifying email).

**How:**
- Define the funnel as an ordered sequence of events with timestamps
- Count a user at step N only if they also completed all prior steps (ordered, not just present)
- Use a time window: a user who signs up in January and converts in July is not in the same funnel as one who converts in 24 hours — define your attribution window explicitly
- Compute drop-off rate at each step, not just conversion at the end

**Example:**
```sql
WITH funnel AS (
  SELECT
    user_id,
    MAX(CASE WHEN event = 'signup'         THEN 1 ELSE 0 END) AS step_1,
    MAX(CASE WHEN event = 'email_verified' THEN 1 ELSE 0 END) AS step_2,
    MAX(CASE WHEN event = 'first_purchase' THEN 1 ELSE 0 END) AS step_3
  FROM events
  WHERE event_date >= '2025-01-01'
  GROUP BY user_id
)
SELECT
  COUNT(*) FILTER (WHERE step_1 = 1)                        AS signup,
  COUNT(*) FILTER (WHERE step_1 = 1 AND step_2 = 1)         AS verified,
  COUNT(*) FILTER (WHERE step_1 = 1 AND step_2 = 1 AND step_3 = 1) AS converted
FROM funnel;
```

**Use for:** Onboarding conversion, checkout abandonment, sales pipeline progression, feature adoption sequences.

---

### 4. Cohort Analysis

**What:** Group users by when they joined (or first performed an action) and track behavior over time relative to that start point.

**Why:** Aggregate retention numbers are misleading. If you acquired 10,000 users in January and 1,000 in February, your March "active users" number mixes two populations with different behavioral profiles. Cohort analysis holds the acquisition period constant, so you can see whether product changes improved retention for users who experienced the new product — separate from users who joined earlier.

**Why this is critical:** Cohort analysis is the correct tool for measuring product improvement. A/B tests tell you whether a change helped in the short term; cohort analysis tells you whether it helped over months.

**How:**
- Define cohort entry: the date of signup, first purchase, or first meaningful action
- Define the metric: retention (did they return?), revenue, feature adoption
- Define the observation period: days/weeks/months since cohort entry (not calendar date)
- Build a cohort matrix: rows = cohort (e.g., signup month), columns = period since entry (month 0, 1, 2...), cells = metric value

**Example:**
```sql
SELECT
  DATE_TRUNC('month', signup_date)          AS cohort_month,
  DATE_DIFF('month', signup_date, activity_date) AS months_since_signup,
  COUNT(DISTINCT user_id)                   AS active_users
FROM user_activity
JOIN users USING (user_id)
WHERE activity_date >= signup_date
GROUP BY 1, 2
ORDER BY 1, 2;
```

**Use for:** Retention curves, lifetime value by acquisition cohort, measuring impact of onboarding changes, subscription churn analysis.

---

### 5. Segmentation and Attribution

**What:** Break a metric down by a dimension (segment) to understand which subgroup drives the aggregate, and assign credit for an outcome to the interactions that caused it.

**Why:** An aggregate metric that is flat can mask a growing segment and a declining segment canceling each other out. Attribution answers "which marketing channel, which feature, which user segment drove this outcome?" — the question that determines where to invest next.

**How:**
- Segment by dimensions relevant to the business: geography, acquisition channel, plan tier, product line
- Apply consistent segment definitions across dashboards — "enterprise" must mean the same thing in every report
- For attribution: define your model explicitly (first-touch, last-touch, linear, time-decay) and document it. Different models produce different answers; the business must choose one and stick to it
- Test for statistical significance before declaring a segment difference meaningful — small segments produce noisy numbers

**Use for:** Revenue by region, conversion by channel, retention by plan tier, feature adoption by persona.

---

## Analytical Workload Design

### Pre-aggregation vs On-Demand

| Approach | When to Use | Trade-Off |
|----------|-------------|-----------|
| **Pre-aggregated Gold tables** | Dashboards with < 5 second SLA, fixed dimensions | Fast queries; requires scheduled pipeline refresh |
| **On-demand query** | Ad-hoc analysis, one-off questions, exploration | Flexible; slow on large datasets without caching |
| **Materialized views** | Frequently queried patterns on large tables | Query-time performance without full pipeline; stale between refreshes |
| **Query caching** | Repeated identical queries (BI tool dashboards) | Zero compute for cache hits; stale data risk |

**Principle:** For dashboards and scheduled reports, pre-aggregate in Gold. For exploration and ad-hoc, use on-demand queries against Silver with appropriate cluster sizing.

---

### Metric Consistency Standards

**Why this matters:** The most common analytics failure is two teams computing the same metric differently and getting different answers. This destroys trust in data and causes teams to maintain their own spreadsheets.

**How:**
- Define every business metric in a single location — a metrics catalog or dbt metrics layer
- A metric definition must include: name, description, SQL or formula, grain (daily/weekly/monthly), filters, and owner
- Computed metrics in dashboards must reference the catalog definition, not inline calculations
- When a metric definition changes, update the catalog and communicate the change — never silently change how a number is computed

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Computing rolling windows at dashboard query time | Scans millions of rows on every page load; dashboards time out | Pre-materialize in Gold with scheduled pipeline |
| Cohort analysis using calendar date instead of cohort-relative date | Mixes populations; seasonal effects look like behavioral effects | Always use time-since-cohort-entry as the X axis |
| Funnel counting without step ordering | Users who skipped earlier steps inflate later-step counts | Only count step N if all prior steps were completed |
| Inconsistent metric definitions across reports | Two correct-looking numbers that disagree; stakeholder distrust | Single metrics catalog; dashboards reference canonical definitions |
| Including test users and internal users in analytics | Inflated metrics that mask real user behavior | Filter internal accounts at the Silver layer, not per query |
| Attributing outcomes without defining a time window | Every interaction gets credit; no meaningful signal | Define attribution window and model explicitly; document the decision |
| Running analytical queries directly against operational databases | Degrades production performance; queries compete with live traffic | Route all analytical queries through the data lake or warehouse |
