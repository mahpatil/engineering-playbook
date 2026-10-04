# Templates Catalog

Production-ready templates for developer context, declarative GitOps continuous delivery, and cryptographic supply chain admission security.

## Template Categories

### 1. Developer Context & Agent Workflows

Standardized templates for configuring AI coding assistants, team context operating systems, and terminal/IDE workflows.

| Template | Focus | Description |
|---|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Agent Project Context | Project context template with placeholders for tech stack, architecture, coding standards, testing, security, and observability. |
| [`build-workflow.md`](./build-workflow.md) | Developer Workflow | Reference multi-pane terminal and IDE workflow for Claude Code, Ghostty, and VS Code. |

### 2. GitOps Continuous Delivery

Declarative, parameterized deployment manifests supporting pull-based GitOps delivery with automated reconciliation, health checks, and sync waves. See [`templates/gitops/README.md`](./gitops/README.md) for sync wave ordering specifications (-2 through 4).

| Template | Engine | Kind | Description |
|---|---|---|---|
| [`argocd-application.yaml`](./gitops/argocd-application.yaml) | ArgoCD | `Application` | Declarative ArgoCD Application with automated sync, pruning, self-healing, retry backoff, and resources finalizer. |
| [`flux-helmrelease.yaml`](./gitops/flux-helmrelease.yaml) | Flux v2 | `HelmRelease` / `GitRepository` | Declarative Flux v2 Git source and HelmRelease with automated reconciliation, health assessment, and rollback. |

### 3. Supply Chain Security & Admission Control

Templates for end-to-end cryptographic supply chain integrity, keyless container image signing, SLSA v1.0 provenance attestation, and Kubernetes cluster admission enforcement. See [`templates/supply-chain/README.md`](./supply-chain/README.md) for architecture and verification details.

| Template | Component | Kind | Description |
|---|---|---|---|
| [`kyverno-cosign-verify.yaml`](./supply-chain/kyverno-cosign-verify.yaml) | Kyverno | `ClusterPolicy` | Cluster policy enforcing keyless Cosign signature and SLSA provenance verification at admission time. |
| [`cosign-slsa-actions.yml`](./supply-chain/cosign-slsa-actions.yml) | GitHub Actions | Reusable Workflow | Reusable CI workflow building container images, signing with Sigstore Cosign via OIDC, and attesting SLSA provenance. |

## Usage Guidelines

1. **Select Template**: Navigate to the category matching your operational requirement.
2. **Substitute Placeholders**: Replace `{{PLACEHOLDER}}` tokens (e.g., `{{APP_NAME}}`, `{{ENVIRONMENT}}`, `{{GITHUB_ORG}}`) with environment-specific values.
3. **Commit & Deploy**: Commit parameter-substituted manifests to your GitOps repository or CI workflow directory.
