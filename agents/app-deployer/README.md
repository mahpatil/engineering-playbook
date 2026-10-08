# app-deployer Agent

Produces a production-ready deployment artefact set for an application service: Dockerfile, Kubernetes manifests, Helm chart, progressive delivery specifications (Argo Rollouts / Flagger), pre-upgrade database migration jobs, smoke test harnesses, and GitHub Actions CI/CD pipelines (GitOps pull promotion or hardened OIDC push).

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
| `deploy/helm/templates/deployment.yaml` | Standard Deployment (rolling strategy or when using Flagger) |
| `deploy/helm/templates/rollout.yaml` | Argo Rollouts canary specification with automated step progression |
| `deploy/helm/templates/canary.yaml` | Flagger Canary specification (`flagger.app/v1beta1`) with automated metric checks |
| `deploy/helm/templates/analysistemplate.yaml` | Real-time PromQL metric evaluation for Argo Rollouts (5xx error rate, P99 latency) |
| `deploy/helm/templates/job-migration.yaml` | Decoupled pre-upgrade database migration Job (Flyway/Liquibase) |
| `tests/smoke/smoke-test.sh` | Automated post-deployment smoke test harness |
| `deploy/k8s/` | Raw Kubernetes manifests (Deployment, Rollout, Canary, Job, etc.) |
| `.github/workflows/ci.yml` | Lint -> test -> static manifest check -> build -> scan -> Cosign sign -> SLSA provenance |
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
| `PROGRESSIVE_DELIVERY_TOOL` | Yes | `argo-rollouts`, `flagger`, or `none` |
| `DELIVERY_MODEL` | No | `gitops-pull` (default for K8s) or `push-oidc` — determines CD workflow pattern |
| `DATABASE_MIGRATION` | No | Object: `enabled`, `engine` (flyway/liquibase), `image` |
| `SUPPLY_CHAIN_SECURITY` | No | Object: `cosign_signing` (bool), `slsa_provenance` (bool) |
| `REPLICAS` | Yes | Min replicas per environment |
| `RESOURCES` | Yes | CPU/memory requests and limits |
| `DEPENDENCIES` | No | Downstream services (used for NetworkPolicy) |

---

## Release Architecture & Delivery Patterns

### 1. Progressive Delivery (Canary)

Supports both Argo Rollouts and Flagger progressive delivery controllers:

- **Argo Rollouts (`PROGRESSIVE_DELIVERY_TOOL: argo-rollouts`)**:
  - **Manifest replacement**: Replaces standard `deployment.yaml` with `rollout.yaml` (`argoproj.io/v1alpha1` `Rollout`) and companion `analysistemplate.yaml` (`argoproj.io/v1alpha1` `AnalysisTemplate`).
  - **Stepped traffic progression**: Canary steps route traffic incrementally: `5%` -> `25%` -> `50%` -> `100%`.
  - **Automated metric analysis**: Runs Prometheus PromQL analysis queries during pause windows:
    - HTTP 5xx error rate ceiling: `sum(rate(http_requests_total{status=~"5.."}[2m])) / sum(rate(http_requests_total[2m])) < 0.001` (< 0.1%).
    - P99 Latency ceiling: `histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[2m])) by (le)) <= 1.15 * baseline`.
  - **Automated abort**: Breaching error or latency thresholds (`consecutiveErrorLimit: 2`) aborts promotion and rolls traffic back to stable pods instantly.
- **Flagger (`PROGRESSIVE_DELIVERY_TOOL: flagger`)**:
  - **Manifest preservation**: Retains standard `deployment.yaml` (`apps/v1` `Deployment`) as the target and generates companion `canary.yaml` (`flagger.app/v1beta1` `Canary` resource).
  - **Target binding**: `targetRef` points to the standard `Deployment`.
  - **Canary analysis**: Iterative traffic shifts via service mesh or ingress provider (Istio, NGINX, Gateway API, Linkerd) with `interval: 1m`, `maxWeight: 100`, and `stepWeight: 25` (5% warm-up or 25% increments).
  - **Metric checks**:
    - Request success rate: `thresholdRange: { min: 99.9 }` (< 0.1% HTTP 5xx errors).
    - Request duration: `thresholdRange: { max: 500 }` (P99 latency <= 1.15x baseline / 500ms).
  - **Automated rollback**: Exceeding failure threshold (`threshold: 2`) immediately aborts canary progression and routes 100% traffic back to the primary/stable deployment.

### 2. Isolated Database Migrations

- **Decoupled execution**: Schema migrations run in isolated ephemeral Kubernetes Jobs prior to application pod rollout. Migrations never run in app startup hooks or entrypoints.
- **Lifecycle guardrails**: Jobs use Helm pre-upgrade hooks (`helm.sh/hook: pre-install,pre-upgrade`, `helm.sh/hook-weight: "-5"`), `activeDeadlineSeconds: 300` (timeout), and `backoffLimit: 1` (fail fast on bad DDL).
- **Zero-downtime safety**: Application code must maintain backward compatibility with old and new schema versions concurrently.

### 3. Automated Smoke Testing

- Script `tests/smoke/smoke-test.sh` runs as an automated validation step in staging and production CD pipelines.
- Verifies liveness and readiness probe endpoints, executes synthetic smoke requests, and validates response latency SLAs (< 500ms) before promotion is finalized.

### 4. Cryptographic Supply Chain & Static Manifest Gates

- **Static manifest validation**: CI runs `deployment-validator --mode=static` against rendered manifests before image push.
- **Keyless image signing**: Signs container digests using Sigstore Cosign via GitHub Actions OIDC identity.
- **SLSA provenance**: Attests build provenance at SLSA Level 3 using verifiable GitHub Actions workflows.

### 5. Delivery Models & CD Pipeline Scaffolding

Scaffolds CD workflows (`cd-dev.yml`, `cd-staging.yml`, `cd-prod.yml`) conforming to either GitOps pull or hardened OIDC push patterns based on `DELIVERY_MODEL`:

- **Declarative GitOps Pull (`DELIVERY_MODEL: gitops-pull`, default for K8s)**:
  - **No cluster credentials in CI**: Workflows never hold `kubeconfig` or static tokens.
  - **Config-repo promotion pattern**:
    - Dev / Staging: After CI passes, workflow commits updated immutable image digests (`sha256:...`) directly to declarative configuration repository (`gitops-manifests`).
    - Production: Workflow opens an automated promotion Pull Request against the configuration repository with required peer approvals and static validation gates.
  - **In-cluster reconciliation**: GitOps engine (ArgoCD or Flux) detects Git commits and synchronizes target environments using sync waves and automated drift self-healing.
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
| Progressive delivery (Argo Rollouts & Flagger, metric analysis) | `standards/detailed/release-engineering/progressive-delivery.md` |
| Isolated pre-upgrade database migration jobs | `standards/detailed/release-engineering/database-migrations.md` |
| Declarative GitOps pull & hardened OIDC push delivery models | `standards/detailed/release-engineering/gitops-promotions.md` |
| Static manifest verification gate in CI | `standards/detailed/release-engineering/gitops-promotions.md` |
| Keyless Cosign signing and SLSA provenance | `standards/detailed/release-engineering/supply-chain-security.md` |
| Trivy image vulnerability scan (blocking HIGH+) | `standards/claude-md/CLAUDE.md` |
| Production manual approval gate | `standards/claude-md/infra/CLAUDE.md` |
