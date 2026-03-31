# Infrastructure Standards

Read `../CLAUDE.md` first. This file extends those principles for infrastructure code (IaC, cloud configuration, networking, security, DR).

---

## Guiding Principles

**Infrastructure is code.** Every piece of infrastructure is defined in version-controlled, peer-reviewed IaC. No manual click-ops in any environment, including development. If it cannot be reproduced from code, it does not exist.

**Cloud-portable by default.** Abstract away provider-specific services where practical. Avoid deep coupling to a single cloud vendor. When vendor-specific services are unavoidable, isolate them behind an interface and document the decision in an ADR.

**Secure by default.** Every resource starts with the most restrictive configuration and permissions are opened only as required. Security is not reviewed at the end — it is designed in.

---

## IaC Standards (Terraform)

### Module Structure

All infrastructure lives in a predictable, environment-agnostic structure:

```
infra/
  modules/              # Reusable, versioned modules (no environment config here)
    networking/
    compute/
    database/
    messaging/
    observability/
    security/
  environments/         # Thin environment-specific composition layers
    dev/
      main.tf
      variables.tf
      terraform.tfvars
    staging/
    prod/
  shared/               # Resources shared across environments (e.g. artifact registry)
```

- **Modules are self-contained.** A module manages one logical resource group (e.g. a VPC, a managed database, a Kubernetes cluster).
- **Environments compose modules.** Environment files are thin — they pass variables into modules. No resource definitions in environment files.
- **Version all module references.** Use `?ref=v1.2.0` for local and remote module sources. Never use an unversioned `main` reference.

```hcl
# GOOD — pinned version
module "vpc" {
  source  = "../../modules/networking"
  version = "1.3.0"

  cidr_block  = var.vpc_cidr
  environment = var.environment
}

# BAD — no version pinning
module "vpc" {
  source = "git::https://github.com/org/infra-modules//networking"
}
```

### State Management

- Remote state is mandatory. Use S3 + DynamoDB (AWS), GCS (GCP), or Azure Blob + Azure Table (Azure).
- State is **never** committed to version control.
- State locking must be enabled. Concurrent state writes corrupt state files.
- Use **separate state files per environment** and per logical domain (`networking`, `compute`, `data`). A single monolithic state file for all infrastructure is a blast-radius risk.
- State backend configuration lives in `backend.tf`, not in `main.tf`.

```hcl
# backend.tf
terraform {
  backend "gcs" {
    bucket = "acme-terraform-state-prod"
    prefix = "services/order-service"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}
```

### Variables and Secrets

- **No hardcoded values.** Every environment-specific value is a variable.
- **No secrets in `.tfvars` files.** Secrets are read from the cloud secrets manager at runtime, or passed via environment variables in CI.
- Sensitive variables must be marked `sensitive = true` in Terraform to suppress logging.
- Outputs that contain sensitive values must also be marked `sensitive = true`.

```hcl
variable "database_password" {
  description = "Master password for the database instance"
  type        = string
  sensitive   = true   # suppressed in plan/apply output
}
```

### Code Quality

- All Terraform must pass `terraform validate` and `terraform fmt` before commit.
- Use `tflint` for linting and best-practice checks.
- Use `tfsec` or `checkov` for security scanning. Block CI on HIGH and CRITICAL findings.
- Run `terraform plan` in CI for every PR. The plan output is posted as a PR comment for review.
- Use `terraform test` or Terratest for module validation.

### Pulumi Alternative

If the team chooses Pulumi:
- Use the same module-composition pattern.
- Stacks map 1:1 to environments.
- Use Pulumi ESC for secrets management — do not embed secrets in stack config.
- All Pulumi programs are written in TypeScript or Go (not Python for new projects).

---

## Cloud-Agnostic Patterns

### What "Cloud-Agnostic" Means in Practice

| Category | Abstraction Approach |
|---|---|
| Object storage | Use a storage interface/port; wire GCS/S3/Azure Blob in config |
| Secrets management | Use a secrets client interface; wire provider SDK in infrastructure layer |
| Managed identities | Use workload identity / IRSA; never static credentials |
| Messaging | Use a message broker interface; wire Kafka/Pub-Sub/SQS in config |
| DNS / Load balancing | Use Kubernetes Ingress / Gateway API; avoid cloud-specific LB annotations where possible |

### Avoid These Vendor Lock-In Patterns

| Pattern | Problem | Alternative |
|---|---|---|
| Cloud-provider-specific SDKs in domain code | Domain tied to vendor | Use ports/adapters |
| Hardcoded region in app code | Cannot move between regions | Inject as env variable |
| Cloud Functions / Lambda for core business logic | Difficult to test and migrate | Use containers; FaaS for glue only |
| Managed ML services for model serving | Expensive, opaque | Containerized model serving (KServe) |

---

## Naming Conventions

Consistent naming makes resources auditable and supports automation.

### Pattern

```
{env}-{project}-{service}-{resource-type}[-{disambiguator}]
```

**Examples:**
```
prod-acme-orders-gke-cluster
staging-acme-payments-cloudsql-primary
dev-acme-api-redis-cache
prod-acme-shared-vpc-main
```

### Rules

- All lowercase with hyphens. No underscores (incompatible with some DNS and cloud resource naming rules).
- `{env}` is one of: `dev`, `staging`, `prod`. No abbreviations like `prd` or `stg`.
- Resource type suffix matches the resource category (e.g. `gke`, `cloudsql`, `redis`, `pubsub`, `bucket`).
- Maximum 63 characters (Kubernetes label limit).

---

## Tagging and Labelling

Every cloud resource must carry the following tags/labels. These are enforced in Terraform via a common `locals` block in every module:

| Tag | Description | Example |
|---|---|---|
| `environment` | Deployment environment | `prod` |
| `project` | Project or product name | `acme-payments` |
| `service` | Owning microservice | `order-service` |
| `team` | Owning team | `platform-engineering` |
| `cost-centre` | Finance cost allocation code | `CC-1042` |
| `managed-by` | Who/what manages this resource | `terraform` |
| `repo` | Source repository URL | `github.com/org/repo` |

```hcl
locals {
  common_labels = {
    environment = var.environment
    project     = var.project
    service     = var.service
    team        = var.team
    cost-centre = var.cost_centre
    managed-by  = "terraform"
    repo        = var.repo_url
  }
}
```

Resources without the required tags fail `checkov` policy checks in CI.

---

## Security Baselines

### Network

- All services run in **private subnets**. Public internet access is only permitted through load balancers and API gateways.
- Use **Private Google Access** / **VNet service endpoints** / **VPC endpoints** for cloud services — no public endpoints.
- Firewall/Security Group rules follow zero-trust: default deny, explicit allow by service identity (not IP range where possible).
- Enable VPC Flow Logs in all environments. Enable Cloud Audit Logs (Admin Activity, Data Access for Restricted data).

### Compute

- No SSH access to production instances. Use Session Manager / OS Login / Azure Bastion.
- Container images are built from approved base images. Base images are scanned for CVEs in CI. Block on CRITICAL CVEs.
- Run containers as non-root. No `privileged: true` in Kubernetes pods.
- Enable Workload Identity for all GKE workloads — no static service account keys.
- Use PodDisruptionBudgets for all production workloads.

```yaml
# Required security context on every container
securityContext:
  runAsNonRoot: true
  runAsUser: 65534
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

### Secrets

- No secrets in Terraform state or tfvars. Reference secrets from the secrets manager at deploy time.
- Rotate secrets automatically where supported (e.g. RDS password rotation, Cloud SQL).
- Secrets have defined TTLs. Long-lived static credentials require explicit approval.
- All secret access is audited and alerted on anomalous access patterns.

### Encryption

- **At rest**: All storage resources encrypted with customer-managed keys (CMKs). No provider-managed-only keys for Restricted data.
- **In transit**: TLS 1.2+ for all connections. TLS 1.0 and 1.1 disabled. mTLS for service-to-service.
- **Database**: Enable encryption at rest. Enable SSL-enforced connections.

### Kubernetes Security (if applicable)

- `NetworkPolicy` resources enforce pod-to-pod isolation. Default deny all ingress/egress.
- Use Pod Security Standards (`restricted` profile for all workloads, `baseline` for system components).
- Enable Kubernetes audit logging.
- Use OPA/Gatekeeper or Kyverno to enforce policy (tag requirements, image registry allow-list, security context rules).
- No `latest` image tags in production manifests.

---

## Disaster Recovery

### RTO and RPO Targets

Define these per service tier before designing DR. Do not default to "as low as possible" — DR cost scales with ambition.

| Tier | Description | RPO | RTO |
|---|---|---|---|
| Tier 1 | Revenue-critical, customer-facing | < 15 min | < 1 hour |
| Tier 2 | Important internal operations | < 1 hour | < 4 hours |
| Tier 3 | Supporting / analytics | < 24 hours | < 8 hours |

### Backup Strategy

- Automated backups on all stateful resources. Never rely on manual backups.
- Test restores regularly — untested backups are not backups. Run restore drills quarterly.
- Backups stored in a separate region from primary. For Tier 1: cross-region continuous replication.
- Point-in-time recovery enabled for all relational databases.
- Backup retention: minimum 7 days for Tier 3; 30 days for Tier 1.

### Multi-Region

For Tier 1 services:
- Active-active or active-passive cross-region topology. Document which model per service.
- Global load balancing with health checks for automatic failover.
- Data replication with RPO-aligned lag monitoring. Alert when replication lag exceeds RPO target.
- Runbook for regional failover tested at least twice per year.

### Chaos Engineering

- Use chaos engineering (Chaos Monkey, Chaos Mesh) to validate DR assumptions in staging.
- Scheduled game days to practice failover procedures.
- Define blast radius before injecting failures.

---

## Cost Optimisation (FinOps)

- Tag all resources with `cost-centre` from day one (see Tagging section).
- Set up billing alerts. Alert at 80% and 100% of monthly budget.
- Review resource utilisation monthly. Right-size underutilised resources.
- Use committed use discounts / reserved instances for stable Tier 1 workloads.
- Auto-scale non-production environments down overnight and on weekends.
- Delete unused resources. Orphaned resources are a cost and security risk.

---

## CI/CD Integration

### Terraform Pipeline

```
PR raised
  → terraform fmt (fail if changes needed)
  → tflint
  → tfsec / checkov (block on HIGH+)
  → terraform validate
  → terraform plan (output posted as PR comment)
  → peer review required

PR merged to main
  → terraform apply (non-prod environments)
  → approval gate
  → terraform apply (production)
```

### Promotion Model

- Infrastructure changes are applied to `dev` → `staging` → `prod` in sequence.
- No manual `terraform apply` in production. All applies go through CI/CD.
- Emergency break-glass procedures are documented and require dual approval.

---

## Related Standards

- `../CLAUDE.md` — Root engineering principles
- `../api/CLAUDE.md` — API gateway and service mesh configuration
- `standards/overall/principles.md` — Cloud-native principles (especially cloud portability)
- `standards/overall/tech-stack.md` — Approved infrastructure tooling
