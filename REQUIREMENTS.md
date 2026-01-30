Title: Requirements Backlog

1. User stories

- As a customer, I can apply a promotional code at checkout to see updated pricing.

- As an admin, I can export orders for a given date range as CSV.

- As a support agent, I can view a customer’s recent failed payments with reasons.

2. Acceptance criteria

- Promo code:

 ▫ Valid codes apply discount rules; invalid codes return actionable errors.

 ▫ Discount reflected in total line item and persisted in order record.

 ▫ Concurrency-safe: two promos cannot double-apply; idempotent updates.

- Order export:

 ▫ CSV includes required columns; time zone normalized to UTC.

 ▫ Pagination and throttling to protect system under load.

- Failed payments view:

 ▫ Displays last 50 failures with error categories and timestamps.

 ▫ Redacts sensitive fields; links to underlying trace IDs.

3. Edge cases

- Expired or usage-limited promo codes.

- Partial refunds and recalculated totals.

- Large exports (≥ 1M rows) require chunking and resumability.

4. Non-functional requirements

- Performance: p95 checkout ≤ 250ms; export jobs complete within SLA for typical ranges.

- Availability: 99.9% for checkout API; worker recovers from transient failures.

- Security: RBAC enforced for admin endpoints; audit logs for sensitive actions.

- Compliance: GDPR deletion flows for PII; retention policies observed.

5. Java specifics (APIs)

- Validate request DTOs; return typed error payloads; ensure idempotent endpoints.

- Transaction boundaries defined; rollbacks on failure; optimistic locking for updates.

6. Python specifics (workers)

- Idempotent job handlers; message deduping; dead-letter queues; retry policies with backoff.

7. Definition of Done

- Code implemented with tests (unit/integration).

- Docs updated; metrics/logs added; feature flag strategy defined.

- Validation pipeline green; PR raised with evidence.