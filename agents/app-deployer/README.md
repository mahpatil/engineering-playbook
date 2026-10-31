# app-deployer Agent

Produces a production-ready deployment artefact set for an application service: Dockerfile, Kubernetes manifests, Helm chart, progressive delivery manifests, pre-upgrade database migration jobs, smoke test harnesses, and GitHub Actions CI/CD pipelines (GitOps pull promotion or hardened OIDC push).

Enforces standards from `standards/claude-md/infra/CLAUDE.md`, `standards/claude-md/CLAUDE.md`, and `standards/detailed/release-engineering/`.

---

## What It Produces

| Artefact | Description |
|---|---|
| `deploy/Dockerfile` | Multi-stage build with distroless/Alpine runtime, non-root user (UID 65534) |
| `deploy/.dockerignore` | Excludes build artefacts, secrets, and dev configs |
| `deploy/helm/Chart.yaml` | Helm chart metadata and semver versioning |
| `deploy/helm/values*.yaml` | Base values + per-environment overrides |
| `deploy/helm/templates/` | Deployment / Rollout / Canary, Service, Ingress, HPA, PDB, NetworkPolicy, ServiceAccount, ConfigMap, ExternalSecret |
| `deploy/helm/templates/rollout.yaml` | Canary / blue-green progressive delivery manifest (when strategy is not rolling) |
| `deploy/helm/templates/job-migration.yaml` | Decoupled pre-upgrade database migration Job  |
| `tests/smoke/smoke-test.sh` | Automated post-deployment smoke test harness |
| `deploy/k8s/` | Raw Kubernetes manifests (Deployment, Rollout, Canary, Job, etc.) |
| `.github/workflows/ci.yml` | Lint -> test -> static manifest check -> build -> scan -> sign -> provenance |
| `.github/workflows/cd-{env}.yml` | Sequential promotion pipelines (GitOps config-repo PR/commit or hardened OIDC push with smoke test gates and production approval) |
| `.github/workflows/security-scan.yml` | Weekly scheduled full image and dependency vulnerability scan |

---

## Inputs

| Field | Required | Description |
|---|---|---|
| `APP_NAME` | Yes | Service name, e.g. `order-service` |
| `PROJECT` | Yes | Project name, e.g. `acme-payments` |
| `TEAM` | Yes | Owning team |
| `LANGUAGE` | Yes | `java`, `dotnet`, `node`, `python`, `go` |
| `FRAMEWORK` | Yes | `springboot`, `aspnetcore`, `express`, `fastapi`, `gin` |
| `CONTAINER_REGISTRY` | Yes | Container registry URL prefix |
| `CLUSTER_NAME` | Yes | Target Kubernetes cluster name |
| `NAMESPACE` | Yes | Kubernetes namespace |
| `ENVIRONMENTS` | Yes | `[dev, staging, prod]` or subset |
| `PORT` | Yes | Application HTTP port |
| `HEALTH_PATH` | Yes | Path prefix for `/health/live` and `/health/ready` |
| `METRICS_PATH` | Yes | Prometheus metrics scrape path |
| `DR_TIER` | Yes | `1`, `2`, or `3` — determines PDB and replica policies |
| `DEPLOYMENT_STRATEGY` | Yes | `rolling`, `canary`, or `blue-green` |
| `DELIVERY_MODEL` | No | `gitops-pull` (default for K8s) or `push-oidc` — determines CD workflow pattern |
| `DATABASE_MIGRATION` | No | Object: `enabled`, `engine`, `image` |
| `SUPPLY_CHAIN_SECURITY` | No | Object: `image_signing` (bool), `provenance` (bool) |
| `REPLICAS` | Yes | Min replicas per environment |
| `RESOURCES` | Yes | CPU/memory requests and limits |
| `DEPENDENCIES` | No | Downstream services (used for NetworkPolicy) |

---

## Release Architecture & Delivery Patterns

### 1. Progressive Delivery (Canary & Blue-Green)

Supports canary and blue-green delivery strategies using standard K8s mechanisms:

- **Canary (`DEPLOYMENT_STRATEGY: canary`)**:
  - **Stepped traffic progression**: Routes traffic incrementally (e.g. 5% -> 25% -> 50% -> 100%) across evaluation windows.
  - **Automated metric analysis**: Evaluates real-time health against defined thresholds: HTTP 5xx error rate < 0.1% and P99 latency <= 1.15x baseline.
  - **Automated abort & rollback**: Immediately aborts progression and shifts 100% traffic back to stable pods upon consecutive threshold breaches.
- **Blue-Green (`DEPLOYMENT_STRATEGY: blue-green`)**:
  - **Isolated environment**: Deploys new revision alongside stable release in an isolated environment without serving live traffic.
  - **Instant cutover & smoke verification**: Executes automated smoke tests against preview workload before atomic traffic switch.
  - **Fast rollback window**: Retains previous stable version during validation window for immediate rollback if post-cutover degradation occurs.

### 2. Isolated Database Migrations

- **Decoupled execution**: Schema migrations run in isolated ephemeral Kubernetes Jobs prior to application pod rollout. Migrations never run in app startup hooks or entrypoints.
- **Lifecycle guardrails**: Jobs use Helm pre-upgrade hooks (pre-install, pre-upgrade), `activeDeadlineSeconds: 300` (timeout), and `backoffLimit: 1` (fail fast on bad DDL).
- **Zero-downtime safety**: Application code must maintain backward compatibility with old and new schema versions concurrently.

### 3. Automated Smoke Testing

- Script `tests/smoke/smoke-test.sh` runs as an automated validation step in staging and production CD pipelines.
- Verifies liveness and readiness probe endpoints, executes synthetic smoke requests, and validates response latency against the agreed SLO before promotion is finalized.

### 4. Cryptographic Supply Chain & Static Manifest Gates

- **Static manifest validation**: CI runs `deployment-validator --mode=static` against rendered manifests before image push.
- **Signing and provenance**: Keyless image signing and build provenance via GitHub Actions OIDC.

### 5. Delivery Models & CD Pipeline Scaffolding

Scaffolds CD workflows (`cd-dev.yml`, `cd-staging.yml`, `cd-prod.yml`) conforming to either GitOps pull or hardened OIDC push patterns based on `DELIVERY_MODEL`:

- **Declarative GitOps Pull (`DELIVERY_MODEL: gitops-pull`, default for K8s)**:
  - **No cluster credentials in CI**: Workflows never hold `kubeconfig` or static tokens.
  - **Config-repo promotion pattern**:
    - Dev / Staging: After CI passes, workflow commits updated immutable image digests (`sha256:...`) directly to declarative configuration repository (`gitops-manifests`).
    - Production: Workflow opens an automated promotion Pull Request against the configuration repository with required peer approvals and static validation gates.
  - **In-cluster reconciliation**: GitOps controller detects Git commits and synchronizes target environments using sync waves and automated drift self-healing.
- **Hardened Push-Based CD (`DELIVERY_MODEL: push-oidc`)**:
  - **Zero permanent credentials**: No static `kubeconfig`, long-lived service account tokens, or cluster certificates in GitHub Secrets.
  - **Keyless OIDC authentication**: Authenticates via GitHub Actions OIDC (`permissions: id-token: write, contents: read`) to cloud IAM (Workload Identity Federation for GCP/Azure, IRSA for AWS) requesting short-lived session tokens with `access_token_lifetime: 900s` (15 minutes).
  - **Deployment concurrency locking**: Enforces `concurrency: { group: <env>-deploy, cancel-in-progress: false }` across all CD workflows to serialize releases and prevent race conditions.
  - **Least-privilege RBAC**: In-cluster ServiceAccount bound strictly to namespace-scoped RBAC (`Role` and `RoleBinding` confined to `<NAMESPACE>`), explicitly prohibiting `ClusterRoleBinding` or `cluster-admin`.

---

## How to Invoke

### Via Claude Code (Interactive)

```bash
cat agents/app-deployer/example-input.md | claude agent run app-deployer
```

### Via Anthropic API

```python
import anthropic

with open("agents/app-deployer/AGENT.md") as f:
    system_prompt = f.read()

with open("agents/app-deployer/example-input.md") as f:
    user_input = f.read()

client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16000,
    system=system_prompt,
    messages=[{"role": "user", "content": user_input}]
)
print(message.content[0].text)
```

---

## Agent Composition Pipeline

```text
infra-provisioner -> app-deployer -> deployment-validator (CI static gate & runtime audit)
```

1. **infra-provisioner**: Provisions cluster, network, and registry infrastructure.
2. **app-deployer**: Emits Dockerfile, Helm/Rollout manifests, migration jobs, smoke tests, and CI/CD pipelines.
3. **deployment-validator**: Validates rendered manifests in CI (`--mode=static`) and audits running cluster state (`--mode=live`).

---

## Standards Enforced

| Standard | Source |
|---|---|
| Multi-stage Dockerfile, non-root user (UID 65534) | `standards/claude-md/infra/CLAUDE.md` |
| Kubernetes security context, PDB, NetworkPolicy | `standards/claude-md/infra/CLAUDE.md` |
| Liveness/readiness probes, Prometheus scrape | `standards/claude-md/CLAUDE.md` |
| Progressive delivery (canary / blue-green, metric analysis) | `standards/detailed/release-engineering/progressive-delivery.md` |
| Isolated pre-upgrade database migration jobs | `standards/detailed/release-engineering/database-migrations.md` |
| Declarative GitOps pull & hardened OIDC push delivery models | `standards/detailed/release-engineering/gitops-promotions.md` |
| Static manifest verification gate in CI | `standards/detailed/release-engineering/gitops-promotions.md` |
| Keyless signing and build provenance | `standards/detailed/release-engineering/supply-chain-security.md` |
| Trivy image vulnerability scan (blocking HIGH+) | `standards/claude-md/CLAUDE.md` |
| Production manual approval gate | `standards/claude-md/infra/CLAUDE.md` |
