# App Deployer Agent

Generates a complete deployment artefact set for an application: multi-stage Dockerfile, Kubernetes manifests, Helm chart scaffold, and a GitHub Actions CI/CD pipeline. Enforces non-root containers, resource limits, security contexts, image scanning, and zero-`latest`-tag policy.

## Prerequisites
- `standards/claude-md/infra/CLAUDE.md` and the relevant backend `CLAUDE.md` present (merged from the standards PR).
- Claude Code CLI or Anthropic API access.
- For CI integration: `ANTHROPIC_API_KEY` stored as a GitHub Actions secret.

---

## Invocation Methods

### 1. Claude Code (interactive)
```bash
claude --agent agents/app-deployer/AGENT.md
# Then describe the deployment, e.g.:
# "Deploy payments-api (Java Spring Boot) to staging on GKE,
#  registry: us-central1-docker.pkg.dev/acme-project/apps"
```

### 2. Claude Code with file input
```bash
claude --agent agents/app-deployer/AGENT.md \
  --print \
  --input agents/app-deployer/example-input.md \
  > deploy/payments-api/generated-artefacts.md
```

### 3. Anthropic API (Python)
```python
import anthropic
from pathlib import Path

client = anthropic.Anthropic(api_key="YOUR_API_KEY_HERE")

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=8096,
    system=Path("agents/app-deployer/AGENT.md").read_text(),
    messages=[{
        "role": "user",
        "content": Path("agents/app-deployer/example-input.md").read_text()
    }],
)
print(response.content[0].text)
```

### 4. GitHub Actions — generate-on-PR
```yaml
# .github/workflows/generate-deploy-artefacts.yml
name: Generate Deployment Artefacts

on:
  workflow_dispatch:
    inputs:
      repo_name:
        required: true
      app_type:
        required: true
        default: java-spring-boot
      target_env:
        required: true
        default: staging
      image_registry:
        required: true

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate deployment artefacts
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/run_agent.py \
            --agent agents/app-deployer/AGENT.md \
            --repo-name "${{ inputs.repo_name }}" \
            --app-type "${{ inputs.app_type }}" \
            --target-env "${{ inputs.target_env }}" \
            --image-registry "${{ inputs.image_registry }}" \
            --output-dir "deploy/${{ inputs.repo_name }}"

      - name: Raise PR with artefacts
        run: |
          git checkout -b "deploy/${{ inputs.repo_name }}-${{ inputs.target_env }}"
          git add deploy/
          git commit -m "deploy: add artefacts for ${{ inputs.repo_name }} ${{ inputs.target_env }}"
          gh pr create \
            --title "deploy: ${{ inputs.repo_name }} ${{ inputs.target_env }}" \
            --body "Auto-generated deployment artefacts."
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo_name` | string | Yes | GitHub repo slug |
| `app_type` | enum | Yes | `java-spring-boot`, `dotnet`, `frontend-react` |
| `target_env` | enum | Yes | `dev`, `staging`, `prod` |
| `image_registry` | string | Yes | Full container registry path |
| `k8s_namespace` | string | No | Default: same as `target_env` |
| `port` | int | No | Container port (default 8080 / 3000) |
| `min_replicas` | int | No | HPA minimum (default 2 for prod) |
| `max_replicas` | int | No | HPA maximum (default 10 for prod) |

---

## Outputs

| File | Description |
|------|-------------|
| `Dockerfile` | Multi-stage, non-root, pinned base images |
| `k8s/deployment.yaml` | Deployment with security context, resources, probes |
| `k8s/service.yaml` | ClusterIP service |
| `k8s/hpa.yaml` | HorizontalPodAutoscaler |
| `k8s/networkpolicy.yaml` | Default-deny with targeted allow rules |
| `k8s/namespace.yaml` | Namespace with labels |
| `helm/Chart.yaml` | Helm chart metadata |
| `helm/values.yaml` | Shared defaults |
| `helm/values-staging.yaml` | Staging overrides |
| `helm/values-prod.yaml` | Production overrides |
| `helm/templates/` | Deployment, Service, HPA templates |
| `.github/workflows/ci-cd.yml` | Full build → scan → push → deploy pipeline |

---

## Pipeline: infra-provisioner → app-deployer

```
1. Run infra-provisioner  →  Terraform applied  →  cluster + registry exist
2. Capture Terraform outputs:
     - k8s_cluster_endpoint
     - image_registry_url
     - k8s_namespace
3. Pass those as inputs to app-deployer
4. Review generated artefacts, commit, and merge
5. The generated ci-cd.yml handles all subsequent deployments automatically
```

---

## Extending for Your Org
- Add `.values-{env}.yaml` overrides for additional environments.
- Extend `networkpolicy.yaml` with org-specific egress rules (e.g. to internal databases).
- Add SAST steps (Sonar, Semgrep) after the build stage in the generated pipeline.
