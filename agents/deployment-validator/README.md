# Deployment Validator Agent

Audits live Kubernetes namespaces or cloud resource groups against the organisation's infrastructure standards. Produces a structured pass/fail compliance report with severity, check IDs, resource references, and a prioritised remediation plan.

## Prerequisites
- `standards/claude-md/infra/CLAUDE.md` present.
- `kubectl` access to the target cluster, or a cloud CLI (`aws`, `gcloud`, `az`) for cloud resource groups.
- Claude Code CLI or Anthropic API access.

---

## Invocation Methods

### 1. kubectl — live namespace audit
```bash
# Capture namespace state
kubectl get deployments,pods,services,networkpolicies,hpa \
  -n payments-staging -o yaml > namespace-dump.yaml

# Run the validator
claude --agent agents/deployment-validator/AGENT.md \
  --print \
  --message "$(cat <<EOF
Audit the following Kubernetes namespace dump.
namespace_or_group: payments-staging
environment: staging
cloud_target: k8s

$(cat namespace-dump.yaml)
EOF
)"
```

### 2. Manifest files — pre-deploy validation
```bash
# Validate manifests before applying to cluster
cat deploy/payments-api/k8s/*.yaml | \
  claude --agent agents/deployment-validator/AGENT.md \
    --print \
    --message "Validate these K8s manifests for payments-api prod deployment before apply.
namespace_or_group: payments-prod
environment: prod
input_type: k8s-manifests"
```

### 3. Anthropic API (Python)
```python
import anthropic
import subprocess
from pathlib import Path

client = anthropic.Anthropic(api_key="YOUR_API_KEY_HERE")

# Fetch live namespace state
ns_dump = subprocess.check_output([
    "kubectl", "get", "deployments,pods,services,networkpolicies,hpa",
    "-n", "payments-staging", "-o", "yaml"
]).decode()

agent_prompt = Path("agents/deployment-validator/AGENT.md").read_text()

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=8096,
    system=agent_prompt,
    messages=[{
        "role": "user",
        "content": f"""Audit this namespace.
namespace_or_group: payments-staging
environment: staging
input_type: k8s-namespace

{ns_dump}"""
    }],
)
print(response.content[0].text)
```

### 4. GitHub Actions — pre-deploy gate
```yaml
# .github/workflows/deployment-validation.yml
name: Deployment Validation

on:
  pull_request:
    paths:
      - 'deploy/**'
      - 'infra/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate deployment manifests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          MANIFESTS=$(cat deploy/**/*.yaml 2>/dev/null || echo "")
          if [ -z "$MANIFESTS" ]; then
            echo "No deployment manifests found, skipping."
            exit 0
          fi

          python scripts/run_agent.py \
            --agent agents/deployment-validator/AGENT.md \
            --content "$MANIFESTS" \
            --input-type k8s-manifests \
            --namespace-or-group "review" \
            --environment "staging" \
            > validation-report.md

      - name: Post report as PR comment
        run: |
          gh pr comment ${{ github.event.pull_request.number }} \
            --body "$(cat validation-report.md)"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Fail on CRITICAL/HIGH findings
        run: |
          if grep -qE 'FAIL.*CRITICAL|FAIL.*HIGH' validation-report.md; then
            echo "::error::Deployment validation failed. Fix CRITICAL/HIGH findings."
            exit 1
          fi
```

### 5. Scheduled compliance scan (cron)
```yaml
# .github/workflows/compliance-scan.yml
name: Scheduled Compliance Scan

on:
  schedule:
    - cron: '0 6 * * 1'   # Every Monday at 06:00 UTC

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/setup-kubectl@v3

      - name: Fetch namespace state
        env:
          KUBECONFIG_DATA: ${{ secrets.KUBECONFIG_PROD }}
        run: |
          echo "$KUBECONFIG_DATA" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
          kubectl get deployments,services,networkpolicies,hpa \
            -n payments-prod -o yaml > namespace-dump.yaml

      - name: Run compliance audit
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/run_agent.py \
            --agent agents/deployment-validator/AGENT.md \
            --input namespace-dump.yaml \
            --input-type k8s-namespace \
            --namespace-or-group payments-prod \
            --environment prod \
            > compliance-report.md

      - name: Open issue if failures found
        if: always()
        run: |
          if grep -q 'Overall status.*FAIL' compliance-report.md; then
            gh issue create \
              --title "Compliance failures in payments-prod ($(date +%Y-%m-%d))" \
              --body "$(cat compliance-report.md)" \
              --label "compliance,prod"
          fi
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `input_type` | enum | Yes | `k8s-namespace`, `k8s-manifests`, `cloud-resource-group` |
| `content` | string | Yes | kubectl YAML output, manifest files, or cloud inventory |
| `namespace_or_group` | string | Yes | Namespace or resource group name |
| `environment` | enum | Yes | `dev`, `staging`, `prod` |
| `cloud_target` | enum | No | `k8s`, `aws`, `gcp`, `azure` (default: `k8s`) |

---

## Output

| Section | Contents |
|---------|---------|
| Report header | Metadata, overall PASS/FAIL, counts |
| Check results table | All checks with PASS/FAIL/UNKNOWN per resource |
| Remediation plan | Prioritised by severity (Immediate → Before Next Release → Planned) |
| Compliance score | Category-level pass rates |

Overall status is `FAIL` if any CRITICAL or HIGH check fails.

---

## Check Categories

| Category | Checks | Key Standards |
|----------|--------|---------------|
| Container Security | 7 | Non-root, no privilege escalation, read-only FS |
| Resource Governance | 7 | CPU/memory requests+limits, HPA, min replicas |
| Health Probes | 3 | Readiness + liveness on every container |
| Image Policy | 3 | No `latest`, approved registry |
| Network Policy | 3 | Default-deny ingress + egress |
| Mandatory Tags | 5 | Environment, Application, Team, ManagedBy, CostCentre |
| Cloud Resources | 6 | No public IPs, encryption, no plain-text secrets |

---

## Extending

- Add custom checks by extending the check tables in `AGENT.md`.
- Add cloud-specific checks (e.g. GCP Workload Identity binding, AWS IMDSv2) under Category 7.
- Integrate the compliance score into a Grafana dashboard via the GitHub Actions JSON output variant.
