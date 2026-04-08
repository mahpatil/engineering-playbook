# infra-provisioner — Example Input

## Invocation

Provision infrastructure for a Tier 1 order management service on GCP.

---

## Request

```
APP_NAME: order-service
PROJECT: acme-payments
TEAM: payments-platform
COST_CENTRE: CC-1042
REPO: github.com/acme-corp/order-service
TARGET_CLOUD: gcp
ENVIRONMENTS: [dev, staging, prod]
DR_TIER: 1
COMPONENTS:
  - database: postgres
  - cache: redis
  - messaging: pubsub
  - compute: kubernetes
  - storage: objectstorage
REGION_PRIMARY: us-central1
REGION_DR: us-east1
```

---

## Context

The order-service is the core revenue path for the ACME Payments platform. It processes all customer purchase orders and interfaces with the payments-gateway service (separate repo).

Key requirements:
- Orders must not be lost during a regional failure (DR Tier 1, RPO < 15 min, RTO < 1 hour)
- PCI-DSS scope: no card numbers stored, but order amounts and customer IDs are Restricted data classification
- Estimated peak load: 500 req/sec at P95 on prod; dev and staging are 10% of prod sizing
- The service emits `order.created`, `order.confirmed`, and `order.cancelled` events via Pub/Sub for downstream consumers
- PostgreSQL used for order state; Redis used for idempotency key caching (24h TTL)
- GCS bucket needed for order export reports (internal access only, no public access)

---

## Expected Output

The agent should produce:

1. `infra/backend.tf` — GCS remote state, separate prefixes per environment
2. `infra/locals.tf` — `common_labels` with all required tags
3. `infra/modules/networking/` — VPC, private subnets (gke-nodes, cloud-sql, redis), public subnet (load balancer), Cloud NAT, Private Google Access, VPC Flow Logs
4. `infra/modules/compute/` — GKE Autopilot cluster, Workload Identity binding for order-service SA
5. `infra/modules/database/` — Cloud SQL PostgreSQL 16, private IP only, CMEK, automated backups with cross-region copy to us-east1, point-in-time recovery, SSL enforced
6. `infra/modules/cache/` — Memorystore for Redis 7.x, AUTH enabled, TLS in-transit, private IP
7. `infra/modules/messaging/` — Pub/Sub topics (order.created, order.confirmed, order.cancelled), DLQ subscriptions, IAM bindings
8. `infra/modules/observability/` — Cloud Monitoring alert policies (CPU, memory, error rate, DB connections, Pub/Sub age), log sink to BigQuery for audit logs
9. `infra/modules/security/` — KMS key ring and keys for DB/GCS/Redis, Secret Manager secret references (DB password, Redis AUTH), IAM service accounts with least-privilege
10. `infra/environments/dev/` — dev composition: smaller machine types, single-zone, no cross-region DR
11. `infra/environments/staging/` — staging composition: prod-like sizing at 50%, zonal HA
12. `infra/environments/prod/` — prod composition: full HA, cross-region DB replication, global load balancer

---

## What a Good Response Looks Like

The agent should:
- Output all files with complete HCL content (no `# TODO` or `# fill in` placeholders except for org-specific values like `COST_CENTRE`)
- Apply `common_labels` to every resource
- Name all resources using the `{env}-acme-payments-order-service-{type}` pattern
- Configure cross-region Cloud SQL replica in `us-east1` for prod (Tier 1 DR)
- Set `deletion_protection = true` on the prod Cloud SQL instance
- Reference secrets by name (`projects/${project_id}/secrets/order-service-db-password/versions/latest`), not by value
- Output a final summary listing manual steps before `terraform apply`
