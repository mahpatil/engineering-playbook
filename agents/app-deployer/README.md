# app-deployer Agent

Produces a complete deployment artefact set for an application service: Dockerfile, Kubernetes manifests, Helm chart, and GitHub Actions CI/CD pipelines. Enforces all container security and deployment standards from `standards/claude-md/infra/CLAUDE.md`.

---

## What It Produces

| Artefact | Description |
|---|---|
| `deploy/Dockerfile` | Multi-stage build with distroless/Alpine runtime, non-root user |
| `deploy/.dockerignore` | Excludes build artefacts, secrets, and dev configs |
| `deploy/helm/Chart.yaml` | Helm chart metadata |
| `deploy/helm/values*.yaml` | Base values + per-environment overrides |
| `deploy/helm/templates/` | Deployment, Service, Ingress, HPA, PDB, NetworkPolicy, ServiceAccount, ConfigMap, ExternalSecret |
| `deploy/k8s/` | Raw Kubernetes manifests (Helm alternative) |
| `.github/workflows/ci.yml` | Build → test → scan → push pipeline |
| `.github/workflows/cd-{env}.yml` | Per-environment deployment pipelines |
| `.github/workflows/security-scan.yml` | Weekly scheduled full image + dependency scan |

---

## Inputs

| Field | Required | Description |
|---|---|---|
| `APP_NAME` | Yes | Service name, e.g. `order-service` |
| `PROJECT` | Yes | Project name, e.g. `acme-payments` |
| `TEAM` | Yes | Owning team |
| `LANGUAGE` | Yes | `java`, `dotnet`, `node`, `python`, `go` |
| `FRAMEWORK` | Yes | `springboot`, `aspnetcore`, `express`, `fastapi`, `gin` |
| `CONTAINER_REGISTRY` | Yes | Registry URL prefix |
| `CLUSTER_NAME` | Yes | Kubernetes cluster name (from infra-provisioner output) |
| `NAMESPACE` | Yes | Kubernetes namespace |
| `ENVIRONMENTS` | Yes | `[dev, staging, prod]` or subset |
| `PORT` | Yes | Application HTTP port |
| `HEALTH_PATH` | Yes | Path prefix for `/health/live` and `/health/ready` |
| `METRICS_PATH` | Yes | Prometheus metrics scrape path |
| `DR_TIER` | Yes | `1`, `2`, or `3` — affects PDB and HPA config |
| `REPLICAS` | Yes | Min replicas per environment |
| `RESOURCES` | Yes | CPU/memory requests and limits |
| `DEPENDENCIES` | No | Downstream services (used for NetworkPolicy) |

---

## How to Invoke

### Via Claude Code (interactive)

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

### Via GitHub Actions (workflow dispatch)

```yaml
# .github/workflows/generate-deploy-artefacts.yml
name: Generate Deployment Artefacts
on:
  workflow_dispatch:
    inputs:
      app_name:
        required: true
      language:
        required: true
      dr_tier:
        required: true
        default: '2'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate deployment artefacts
        uses: anthropics/claude-code-action@v1
        with:
          agent-system-prompt-file: agents/app-deployer/AGENT.md
          prompt: |
            APP_NAME: ${{ inputs.app_name }}
            LANGUAGE: ${{ inputs.language }}
            DR_TIER: ${{ inputs.dr_tier }}
            PROJECT: acme
            TEAM: platform-engineering
            CONTAINER_REGISTRY: us-central1-docker.pkg.dev/acme-prod/services
            CLUSTER_NAME: prod-acme-${{ inputs.app_name }}-gke-cluster
            NAMESPACE: ${{ inputs.app_name }}
            PORT: 8080
            HEALTH_PATH: /actuator
            METRICS_PATH: /actuator/prometheus
            ENVIRONMENTS: [dev, staging, prod]
            REPLICAS:
              dev: 1
              staging: 2
              prod: 3
            RESOURCES:
              requests: { cpu: "250m", memory: "512Mi" }
              limits: { cpu: "1000m", memory: "1Gi" }
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
      - uses: peter-evans/create-pull-request@v6
        with:
          title: "feat(deploy): add deployment artefacts for ${{ inputs.app_name }}"
```

---

## Composition with infra-provisioner

Run infra-provisioner first to generate the cluster and namespace. Then pass the cluster name and registry from its output into app-deployer:

```
infra-provisioner → app-deployer → deployment-validator (post-deploy audit)
```

---

## Standards Enforced

| Standard | Source |
|---|---|
| Multi-stage Dockerfile, non-root user | `infra/CLAUDE.md` § Security Baselines → Compute |
| Kubernetes security context (all fields) | `infra/CLAUDE.md` § Kubernetes Security |
| No `latest` tags in staging/prod | `infra/CLAUDE.md` § Kubernetes Security |
| PodDisruptionBudget | `infra/CLAUDE.md` § Kubernetes Security |
| NetworkPolicy explicit allow model | `infra/CLAUDE.md` § Security Baselines → Network |
| Liveness/readiness probes | `CLAUDE.md` § Observability |
| Prometheus annotations | `CLAUDE.md` § Observability → Metrics |
| Trivy scan blocking on HIGH+ | `CLAUDE.md` § Security → Dependency Management |
| Manual approval gate for production | `infra/CLAUDE.md` § CI/CD Integration |
| Secrets via secrets manager references | `CLAUDE.md` § Security → Non-Negotiables |
