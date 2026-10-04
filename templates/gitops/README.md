# GitOps Manifest Templates

Production-grade, parameterized GitOps deployment manifests for pull-based continuous delivery using ArgoCD and Flux v2.

## Manifest Templates

| Template | Engine | API Version | Kind | Description |
|---|---|---|---|---|
| [`argocd-application.yaml`](./argocd-application.yaml) | ArgoCD | `argoproj.io/v1alpha1` | `Application` | Declarative ArgoCD Application with automated sync, prune, self-heal, retry backoff, and resources finalizer. |
| [`flux-helmrelease.yaml`](./flux-helmrelease.yaml) | Flux v2 | `source.toolkit.fluxcd.io/v1` / `helm.toolkit.fluxcd.io/v2` | `GitRepository` / `HelmRelease` | Declarative Flux v2 Git source and HelmRelease with automated reconciliation, retries, and rollback. |

## Placeholder Dictionary

| Placeholder | Description | Example Values |
|---|---|---|
| `{{APP_NAME}}` | Logical application or microservice identifier | `payment-service`, `order-api` |
| `{{ENVIRONMENT}}` | Deployment target tier or environment | `dev`, `staging`, `prod` |
| `{{GITOPS_REPO_URL}}` | HTTPS or SSH Git URL containing Helm charts | `https://github.com/org/gitops-repo.git` |
| `{{TARGET_REVISION}}` | Git branch, commit SHA, or tag target (ArgoCD) | `main`, `v1.4.0`, `HEAD` |
| `{{BRANCH}}` | Git branch tracked by Flux GitRepository | `main`, `release/v1` |
| `{{CHART_PATH}}` | Repository-relative path to Helm chart root | `deploy/helm/payment-service` |
| `{{NAMESPACE}}` | Target Kubernetes workload namespace | `payment-service-prod`, `payments` |

## Sync Wave Ordering Guide (-2 to 4)

Sync waves define deterministic phased resource provisioning during continuous delivery reconciliation. Resources execute in ascending order (-2 through 4).

| Wave | Lifecycle Phase | Target Resources | Operational Guarantee |
|:---|:---|:---|:---|
| **-2** | Cluster Infrastructure & Identity | `Namespace`, `CustomResourceDefinition`, `ServiceAccount`, `ClusterRoleBinding` | Ensures namespaces, RBAC primitives, and CRDs exist before any consumer workloads initialize. |
| **-1** | Baseline Configuration & Networking | `ConfigMap`, `Secret`, `ExternalSecret`, `NetworkPolicy`, `ResourceQuota` | Provisions configuration and default-deny network perimeters before services boot. |
| **0** | Pre-Sync Lifecycle Hooks | Schema Migration `Job` (`helm.sh/hook: pre-upgrade`, `argocd.argoproj.io/hook: PreSync`) | Executes backward-compatible database schema migrations. Halts promotion on non-zero exit. |
| **1** | Stateful Tier & Shared Dependencies | `StatefulSet`, `PersistentVolumeClaim`, `Redis`, message broker dependencies | Ensures backing databases and caches are healthy before frontend workloads attach. |
| **2** | Primary Application Workloads | `Deployment`, `Rollout` (Argo Rollouts), `Service`, `PodDisruptionBudget` | Deploys core service containers and initiates progressive canary traffic routing. |
| **3** | Ingress, Gateways & Edge Routing | `Ingress`, `HTTPRoute` (Gateway API), `Certificate`, external DNS records | Exposes service endpoints externally once application pods pass readiness checks. |
| **4** | Post-Sync Verification & Auditing | Smoke Test `Job` (`argocd.argoproj.io/hook: PostSync`), `deployment-validator` audit | Executes end-to-end verification and compliance audits against the live cluster. |

### Annotating Resources with Sync Waves

Annotate Kubernetes manifests to assign their respective wave order:

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "2"
```

## Deployment Commands & Workflows

### 1. Template Parameter Substitution

Substitute placeholders before applying manifests into target clusters:

```bash
export APP_NAME="payment-service"
export ENVIRONMENT="prod"
export GITOPS_REPO_URL="https://github.com/my-org/gitops-manifests.git"
export TARGET_REVISION="main"
export BRANCH="main"
export CHART_PATH="deploy/helm/payment-service"
export NAMESPACE="payment-service-prod"

# Substitute and render manifest
envsubst < templates/gitops/argocd-application.yaml > argocd-rendered.yaml
envsubst < templates/gitops/flux-helmrelease.yaml > flux-rendered.yaml
```

### 2. ArgoCD Operations

Deploy and manage the application via ArgoCD CLI and `kubectl`:

```bash
# Apply Application manifest into ArgoCD controller namespace
kubectl apply -n argocd -f argocd-rendered.yaml

# Inspect application sync and health status
argocd app get ${APP_NAME}-${ENVIRONMENT}

# Trigger immediate manual sync with pruning enabled
argocd app sync ${APP_NAME}-${ENVIRONMENT} --prune

# Watch rollout and resource tree progression
argocd app wait ${APP_NAME}-${ENVIRONMENT} --health
```

### 3. Flux v2 Operations

Deploy and reconcile via Flux CLI and `kubectl`:

```bash
# Apply GitRepository and HelmRelease manifests
kubectl apply -f flux-rendered.yaml

# Reconcile Git repository source immediately
flux reconcile source git ${APP_NAME} -n ${NAMESPACE}

# Trigger immediate HelmRelease reconciliation
flux reconcile hr ${APP_NAME}-${ENVIRONMENT} -n ${NAMESPACE} --with-source

# Verify reconciliation status and conditions
flux get helmreleases -n ${NAMESPACE}
```
