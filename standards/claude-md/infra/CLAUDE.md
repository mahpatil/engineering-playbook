# Infrastructure Standards

Extends ../CLAUDE.md.

Every resource is defined in reviewed IaC; no click-ops in any environment. Isolate vendor-specific services behind an interface.

## Tooling
- Terraform >= 1.10 (or OpenTofu >= 1.10) is the default. Pulumi is allowed by ADR: one stack per environment, secrets via Pulumi ESC, TypeScript or Go.
- Pin providers (`~> 5.0` style) and commit `.terraform.lock.hcl`.

## Layout
```
infra/
  modules/        # reusable, no environment config
  environments/{dev,staging,prod}/   # thin composition: module calls and variables only
  shared/         # cross-environment resources (artifact registry, DNS)
```
- One module per logical resource group (VPC, database, cluster). Environments contain no resource definitions.
- Registry and git module sources are version-pinned (`version = "1.3.0"` or `?ref=v1.3.0`). The `version` argument is invalid for local paths; local modules are versioned with the repo. Never reference `main`.

## State
- Remote backend with locking is mandatory, configured in `backend.tf`; state is never committed.
  - AWS: S3 with `use_lockfile = true` (DynamoDB locking is deprecated).
  - GCP: GCS. Azure: Blob (native lease locking).
- Separate state per environment and per domain (`networking`, `compute`, `data`) to limit blast radius.
- State holds secrets in plaintext: encrypt the bucket with a CMK and restrict access to CI and break-glass roles.

## Variables and secrets
- No hardcoded environment values; no secrets in `.tfvars`.
- Read secrets from the secrets manager (data sources or ephemeral resources/write-only arguments on Terraform >= 1.11); otherwise they land in state.
- Mark sensitive variables and outputs `sensitive = true`.

## Naming and tags
- Pattern: `{env}-{project}-{service}-{type}[-{n}]`, lowercase hyphenated, <= 63 chars. `env` is `dev`, `staging` or `prod`.
- Required tags/labels from a shared `locals.common_labels`: `environment`, `project`, `service`, `team`, `cost-centre`, `managed-by=terraform`, `repo`. Use lowercase values (GCP labels reject uppercase).
- Missing tags fail checkov (custom policy) in CI.

## Environments and promotion
- Order: `dev` -> `staging` -> `prod`. Production applies only via CI after an approval gate; no manual `apply`. Break-glass needs dual approval and a follow-up PR.
- Budget alerts at 80% and 100%; non-prod scales down off-hours.

## Policy-as-code (CI gates)
```
PR:    terraform fmt -check -> tflint -> terraform validate -> checkov (block HIGH+)
       -> terraform plan (posted to PR) -> conftest/OPA on plan JSON -> review
Merge: apply non-prod -> approval -> apply prod
```
- `tfsec` is superseded by Trivy: use `trivy config` or checkov, not both for the same rules.
- Module tests: `terraform test` (native) or Terratest.

## Runtime baselines (enforced by policy, not review)
- Workloads in private subnets; public ingress only via load balancer or gateway; use private endpoints for cloud services. Default-deny firewall and `NetworkPolicy`.
- Kubernetes: Pod Security Standards `restricted` for workloads, `baseline` for system namespaces; enforce with Kyverno or Gatekeeper:
  - `runAsNonRoot`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem`, drop `ALL` capabilities.
  - Images from an approved registry, pinned by tag or digest (never `latest`).
  - PodDisruptionBudget on production workloads.
- CMKs for Confidential and Restricted storage.

## Disaster recovery
| Tier | Scope | RPO | RTO | Backup retention |
|---|---|---|---|---|
| 1 | Revenue-critical | < 15 min | < 1 h | >= 30 d, cross-region |
| 2 | Internal operations | < 1 h | < 4 h | >= 14 d |
| 3 | Supporting / analytics | < 24 h | < 8 h | >= 7 d |

- Automated backups and point-in-time recovery on all relational databases. Restore drills quarterly.
- Tier 1: documented active-active or active-passive topology, replication-lag alert at the RPO, failover runbook exercised twice a year.
