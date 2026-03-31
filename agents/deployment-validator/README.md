# deployment-validator Agent

Audits a live Kubernetes deployment or Terraform state against every control in `standards/claude-md/infra/CLAUDE.md`, producing a structured compliance report with PASS/FAIL/WARN per control and prioritised remediations.

---

## What It Produces

| Section | Description |
|---|---|
| **Overall Score** | `n/total controls passing (percentage%)` |
| **Control Results** | Table per category: Security, Network, Resilience, Observability, Tagging, DR |
| **Failures** | Each failed control with standard citation, risk, remediation YAML/HCL, effort estimate |
| **Unknown Controls** | Controls that couldn't be evaluated + commands to gather missing evidence |
| **Remediation Priority** | Risk-ordered list |
| **Compliance Certificate** | One sentence for a compliance register or audit trail |

---

## Control Categories

| Category | Controls Checked |
|---|---|
| **Security (SEC)** | Non-root user, no privilege escalation, read-only root FS, capabilities dropped, no privileged/hostNetwork, ServiceAccount token disabled, no `latest` image, secrets via ExternalSecret |
| **Network (NET)** | NetworkPolicy present, default deny ingress/egress, no wildcard selectors, no public database |
| **Resilience (RES)** | PodDisruptionBudget, HPA, resource requests/limits, graceful shutdown |
| **Observability (OBS)** | Liveness/readiness probes, Prometheus scrape annotations |
| **Tagging (TAG)** | All 6 required labels, naming convention |
| **DR & Backup (DR)** | Automated backups, PITR, cross-region (Tier 1), deletion protection |

---

## Gathering Evidence

Run these commands before invoking the agent:

```bash
NAMESPACE=order-service

kubectl get deployments -n $NAMESPACE -o yaml    > evidence/deployments.yaml
kubectl get pods -n $NAMESPACE -o yaml           > evidence/pods.yaml
kubectl get networkpolicies -n $NAMESPACE -o yaml > evidence/netpolicies.yaml
kubectl get hpa -n $NAMESPACE -o yaml            > evidence/hpa.yaml
kubectl get pdb -n $NAMESPACE -o yaml            > evidence/pdb.yaml
kubectl get serviceaccounts -n $NAMESPACE -o yaml > evidence/serviceaccounts.yaml
kubectl get secrets -n $NAMESPACE               > evidence/secrets-list.txt  # names only

# For Terraform/cloud resources:
terraform show -json                             > evidence/terraform-state.json

# GCP examples:
gcloud sql instances describe prod-acme-db --format=json > evidence/cloudsql.json
gcloud storage buckets describe gs://prod-acme-reports   > evidence/bucket.json
```

---

## How to Invoke

### Via Claude Code (interactive)

```bash
cat agents/deployment-validator/example-input.md | claude agent run deployment-validator
```

### Via Anthropic API

```python
import anthropic
import subprocess

def validate_deployment(namespace: str, environment: str, dr_tier: int) -> dict:
    with open("agents/deployment-validator/AGENT.md") as f:
        system_prompt = f.read()

    evidence_blocks = []
    commands = [
        ("kubectl_get_deployments",     f"kubectl get deployments -n {namespace} -o yaml"),
        ("kubectl_get_networkpolicy",   f"kubectl get networkpolicies -n {namespace} -o yaml"),
        ("kubectl_get_hpa",             f"kubectl get hpa -n {namespace} -o yaml"),
        ("kubectl_get_pdb",             f"kubectl get pdb -n {namespace} -o yaml"),
        ("kubectl_get_serviceaccounts", f"kubectl get sa -n {namespace} -o yaml"),
    ]

    for evidence_type, cmd in commands:
        try:
            output = subprocess.check_output(cmd.split(), stderr=subprocess.DEVNULL).decode()
            block = f"  - type: {evidence_type}\n    content: |\n"
            block += "\n".join(f"      {line}" for line in output.splitlines())
            evidence_blocks.append(block)
        except subprocess.CalledProcessError:
            pass

    prompt = f"""ENVIRONMENT: {environment}
CLOUD: gcp
SERVICE: {namespace}
PROJECT: acme-payments
DR_TIER: {dr_tier}

EVIDENCE:
{chr(10).join(evidence_blocks)}"""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}]
    )

    report = message.content[0].text
    compliant = "NON-COMPLIANT" not in report
    return {"compliant": compliant, "report": report}
```

### Via GitHub Actions (scheduled weekly audit)

```yaml
# .github/workflows/compliance-audit.yml
name: Weekly Compliance Audit
on:
  schedule:
    - cron: '0 6 * * 1'   # Every Monday at 06:00 UTC
  workflow_dispatch:

jobs:
  audit-prod:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_CREDENTIALS_READONLY }}

      - uses: google-github-actions/get-gke-credentials@v2
        with:
          cluster_name: prod-acme-payments-gke-cluster
          location: us-central1

      - name: Gather evidence
        run: |
          kubectl get deployments -n order-service -o yaml > deps.yaml
          kubectl get networkpolicies -n order-service -o yaml > netpol.yaml
          kubectl get hpa -n order-service -o yaml > hpa.yaml
          kubectl get pdb -n order-service -o yaml > pdb.yaml
          kubectl get serviceaccounts -n order-service -o yaml > sa.yaml

      - name: Run compliance audit
        id: audit
        uses: anthropics/claude-code-action@v1
        with:
          agent-system-prompt-file: agents/deployment-validator/AGENT.md
          prompt: |
            ENVIRONMENT: prod
            CLOUD: gcp
            SERVICE: order-service
            PROJECT: acme-payments
            DR_TIER: 1
            EVIDENCE:
              - type: kubectl_get_deployments
                content: |
                  $(cat deps.yaml | head -500)
              - type: kubectl_get_networkpolicy
                content: |
                  $(cat netpol.yaml)
              - type: kubectl_get_hpa
                content: |
                  $(cat hpa.yaml)
              - type: kubectl_get_pdb
                content: |
                  $(cat pdb.yaml)
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Open issue if non-compliant
        if: contains(steps.audit.outputs.result, 'NON-COMPLIANT')
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `[Compliance] prod order-service NON-COMPLIANT - ${new Date().toISOString().split('T')[0]}`,
              labels: ['compliance', 'priority-high'],
              body: process.env.AUDIT_REPORT
            })
        env:
          AUDIT_REPORT: ${{ steps.audit.outputs.result }}
```

---

## Composition

```
infra-provisioner → app-deployer → (first deploy) → deployment-validator
                                                     (weekly schedule)  → deployment-validator
```

---

## Standards Enforced

| Control | Source |
|---|---|
| Container security context | `infra/CLAUDE.md` § Security Baselines → Kubernetes |
| NetworkPolicy structure | `infra/CLAUDE.md` § Security Baselines → Network |
| Required labels | `infra/CLAUDE.md` § Tagging and Labelling |
| Naming convention | `infra/CLAUDE.md` § Naming Conventions |
| PDB and HPA | `infra/CLAUDE.md` § Kubernetes Security |
| Liveness/readiness probes | `CLAUDE.md` § Observability |
| DR configuration | `infra/CLAUDE.md` § Disaster Recovery |
| Secret management | `CLAUDE.md` § Security → Non-Negotiables |
