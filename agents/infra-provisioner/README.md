# infra-provisioner Agent

Generates production-ready Terraform modules for a new application service, enforcing every standard in `standards/claude-md/infra/CLAUDE.md`.

---

## What It Produces

Given an app description and target cloud, the agent outputs a complete `infra/` directory:

| Artefact | Description |
|---|---|
| `infra/backend.tf` | Remote state configuration (GCS / S3+DynamoDB / Azure Blob) |
| `infra/locals.tf` | `common_labels` map applied to every resource |
| `infra/modules/networking/` | VPC, subnets (private/public), NAT, service endpoints, flow logs |
| `infra/modules/compute/` | GKE / EKS / AKS cluster with node pools and workload identity |
| `infra/modules/database/` | Managed relational database with encryption, private endpoint, backups |
| `infra/modules/cache/` | Redis cluster with TLS, auth, private endpoint |
| `infra/modules/messaging/` | Kafka / Pub/Sub / SQS topic/queue with access policy |
| `infra/modules/observability/` | Monitoring dashboards, alert policies, log sinks |
| `infra/modules/security/` | IAM, KMS/CMK keys, secret references, firewall/network policies |
| `infra/environments/{env}/` | Thin environment compositions (dev / staging / prod) |

---

## Inputs

Provide a structured request (copy from `example-input.md` and fill in your values):

| Field | Required | Description |
|---|---|---|
| `APP_NAME` | Yes | Service name, e.g. `order-service` |
| `PROJECT` | Yes | Project/product name, e.g. `acme-payments` |
| `TEAM` | Yes | Owning team name |
| `COST_CENTRE` | Yes | Finance cost allocation code |
| `REPO` | Yes | Source repository URL |
| `TARGET_CLOUD` | Yes | `aws`, `gcp`, or `azure` |
| `ENVIRONMENTS` | Yes | Which environments to generate: `dev`, `staging`, `prod` |
| `DR_TIER` | Yes | `1` (revenue-critical), `2` (important), or `3` (supporting) |
| `COMPONENTS` | Yes | Which infrastructure components to include |
| `REGION_PRIMARY` | Yes | Primary region identifier |
| `REGION_DR` | Tier 1 & 2 | DR / secondary region |

---

## How to Invoke

### Via Claude Code (interactive)

```bash
# From your project root
cat agents/infra-provisioner/example-input.md | claude agent run infra-provisioner
```

Or paste the input directly in a Claude Code session with the agent loaded:

```
@infra-provisioner

APP_NAME: order-service
PROJECT: acme-payments
TEAM: platform-engineering
COST_CENTRE: CC-1042
REPO: github.com/acme/order-service
TARGET_CLOUD: gcp
ENVIRONMENTS: [dev, staging, prod]
DR_TIER: 1
COMPONENTS:
  - database: postgres
  - cache: redis
  - compute: kubernetes
REGION_PRIMARY: us-central1
REGION_DR: us-east1
```

### Via Anthropic API

```python
import anthropic

with open("agents/infra-provisioner/AGENT.md") as f:
    system_prompt = f.read()

with open("agents/infra-provisioner/example-input.md") as f:
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
# .github/workflows/infra-bootstrap.yml
name: Infra Bootstrap
on:
  workflow_dispatch:
    inputs:
      app_name:
        description: 'Service name'
        required: true
      target_cloud:
        description: 'Target cloud (aws/gcp/azure)'
        required: true
      dr_tier:
        description: 'DR Tier (1/2/3)'
        required: true

jobs:
  generate-infra:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate Terraform modules
        uses: anthropics/claude-code-action@v1
        with:
          agent-system-prompt-file: agents/infra-provisioner/AGENT.md
          prompt: |
            APP_NAME: ${{ inputs.app_name }}
            TARGET_CLOUD: ${{ inputs.target_cloud }}
            DR_TIER: ${{ inputs.dr_tier }}
            PROJECT: acme
            TEAM: platform-engineering
            COST_CENTRE: CC-1042
            REPO: github.com/${{ github.repository }}
            ENVIRONMENTS: [dev, staging, prod]
            COMPONENTS:
              - database: postgres
              - cache: redis
              - compute: kubernetes
            REGION_PRIMARY: us-central1
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
      - name: Create PR with generated infra
        uses: peter-evans/create-pull-request@v6
        with:
          title: "feat(infra): bootstrap ${{ inputs.app_name }} terraform modules"
          branch: "feat/infra-bootstrap-${{ inputs.app_name }}"
```

---

## After Generation

The agent outputs a **summary** at the end of its response covering:

1. **Resources created** — list of all Terraform resources generated
2. **Estimated cost** — rough monthly cost range per environment
3. **Security controls** — which baseline controls were applied
4. **DR configuration** — backup strategy, RTO/RPO alignment
5. **Manual steps** — what you must do before `terraform apply`:
   - Populate secrets in the cloud secrets manager
   - Set real values in `terraform.tfvars` (copy from `.example`)
   - Configure DNS delegation (if applicable)
   - Review and set `COST_CENTRE` tag values with Finance

---

## Composition: Next Steps

After running infra-provisioner, run **app-deployer** to generate Kubernetes manifests and CI/CD for the same service. The app-deployer will reference the infrastructure resources (cluster name, namespace, secret references) generated here.

```
infra-provisioner → app-deployer → deployment-validator (post-deploy audit)
```

---

## Standards Enforced

| Standard | Source |
|---|---|
| Naming convention | `infra/CLAUDE.md` § Naming Conventions |
| Resource tagging | `infra/CLAUDE.md` § Tagging and Labelling |
| Remote state management | `infra/CLAUDE.md` § State Management |
| Zero-trust networking | `infra/CLAUDE.md` § Security Baselines → Network |
| Kubernetes security context | `infra/CLAUDE.md` § Security Baselines → Kubernetes |
| DR tier matrix | `infra/CLAUDE.md` § Disaster Recovery |
| Encryption at rest and in transit | `infra/CLAUDE.md` § Security Baselines → Encryption |
| FinOps tagging | `infra/CLAUDE.md` § Cost Optimisation |
