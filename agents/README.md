# Claude Agent Suite — Engineering Standards Enforcement

This directory contains a suite of Claude agents designed to provision infrastructure, deploy applications, scaffold code, and enforce engineering standards across every stage of the software delivery lifecycle.

Every agent is **CLAUDE.md-aware**: its system prompt references and enforces the standards defined in `standards/claude-md/`. When you update those standards, the agents automatically reflect them.

---

## Agents

| Agent | Purpose | Inputs | Primary Outputs |
|---|---|---|---|
| [infra-provisioner](./infra-provisioner/) | Generate Terraform modules for a new service | App description, target cloud | Terraform modules, backend config, tagging locals |
| [app-deployer](./app-deployer/) | Produce a complete deployment artefact set | Repo description, environment | Dockerfile, K8s manifests, Helm chart, GitHub Actions CI |
| [api-scaffolder](./api-scaffolder/) | Scaffold OpenAPI spec + route stubs | API name, resources, language | `openapi.yaml`, controller/handler stubs, validator stubs |
| [standards-reviewer](./standards-reviewer/) | Flag CLAUDE.md violations in code or a PR diff | Code or diff | Structured findings with severity + remediation |
| [deployment-validator](./deployment-validator/) | Audit a live environment against infra standards | K8s context or Terraform state | Compliance report with PASS/FAIL/WARN per control |

---

## How Agents Compose

Agents are designed to chain. The canonical provisioning pipeline is:

```
Engineer provides:
  - App name and description
  - Target cloud (AWS / GCP / Azure)
  - Environment (dev / staging / prod)
  - API resources (e.g. Orders, Customers)

       ┌─────────────────────┐
       │   infra-provisioner  │  →  Terraform modules (VPC, DB, GKE/EKS/AKS, Redis, IAM)
       └──────────┬──────────┘
                  │ outputs: infra/ directory
                  ▼
       ┌─────────────────────┐
       │    api-scaffolder    │  →  openapi.yaml + route stubs (Java or .NET)
       └──────────┬──────────┘
                  │ outputs: docs/api/, src/api/
                  ▼
       ┌─────────────────────┐
       │    app-deployer      │  →  Dockerfile, k8s manifests, Helm chart, GitHub Actions
       └──────────┬──────────┘
                  │ outputs: deploy/, .github/workflows/
                  ▼
       ┌─────────────────────┐      ┌──────────────────────┐
       │  standards-reviewer  │  +   │ deployment-validator  │
       └─────────────────────┘      └──────────────────────┘
         Pre-merge: reviews code        Post-deploy: audits live
         against CLAUDE.md standards    infra against standards
```

### Practical Integration Patterns

**Pattern 1: New Service Bootstrap (fully automated)**
```bash
# In a new repo, run sequentially:
claude --agent infra-provisioner < agents/infra-provisioner/example-input.md
claude --agent api-scaffolder    < agents/api-scaffolder/example-input.md
claude --agent app-deployer      < agents/app-deployer/example-input.md
```

**Pattern 2: PR Gate (CI-integrated)**
```yaml
# .github/workflows/standards-review.yml
- uses: anthropics/claude-code-action@v1
  with:
    agent: standards-reviewer
    input: ${{ github.event.pull_request.diff_url }}
```

**Pattern 3: Compliance Audit (scheduled)**
```yaml
# Run deployment-validator weekly against prod
- uses: anthropics/claude-code-action@v1
  with:
    agent: deployment-validator
    input: "cluster=prod-acme-gke environment=prod"
```

---

## Standards Inheritance

All agents inherit from and enforce the CLAUDE.md hierarchy:

```
standards/claude-md/CLAUDE.md               ← root principles (all agents)
  ├── infra/CLAUDE.md                        ← infra-provisioner, app-deployer, deployment-validator
  ├── api/CLAUDE.md                          ← api-scaffolder, standards-reviewer
  ├── backend/java/CLAUDE.md                 ← api-scaffolder (Java), standards-reviewer
  ├── backend/dotnet/CLAUDE.md               ← api-scaffolder (.NET), standards-reviewer
  └── frontend/CLAUDE.md                     ← standards-reviewer
```

When any CLAUDE.md is updated, agents that reference it immediately reflect the new standards — no agent code changes needed.

---

## Forking and Extending for Enterprise Teams

### Customising Standards

1. Fork `standards/claude-md/` and modify the CLAUDE.md files for your organisation's specific requirements (approved libraries, internal tooling, compliance frameworks).
2. Update the `STANDARDS_ROOT` path in each `AGENT.md` if the standards live in a different location.
3. Add organisation-specific sections to any AGENT.md under `## Organisation-Specific Context`.

### Adding a New Agent

```
agents/
  my-new-agent/
    AGENT.md            ← system prompt: what the agent is and how it behaves
    README.md           ← how to invoke, inputs, outputs, integration example
    example-input.md    ← realistic example invocation
```

Follow the existing AGENT.md structure:
1. **Identity** — what this agent is and does
2. **Standards references** — which CLAUDE.md files it enforces
3. **Input format** — structured schema for inputs
4. **Output format** — what the agent produces and in what format
5. **Behaviour rules** — non-negotiable constraints
6. **Output template** — concrete template for each deliverable

### Registering Agents with Claude Code

In your project's `.claude/settings.json`:

```json
{
  "agents": {
    "infra-provisioner":    "agents/infra-provisioner/AGENT.md",
    "app-deployer":         "agents/app-deployer/AGENT.md",
    "api-scaffolder":       "agents/api-scaffolder/AGENT.md",
    "standards-reviewer":   "agents/standards-reviewer/AGENT.md",
    "deployment-validator": "agents/deployment-validator/AGENT.md"
  }
}
```

Then invoke with: `claude agent run infra-provisioner`

### Versioning Agents

Tag agent releases alongside standards releases. A `v1.2.0` of the standards suite should have a corresponding `v1.2.0` tag for agents. Consumers can pin to a version:

```bash
git checkout tags/v1.2.0 -- agents/
```

---

## Security Considerations

- Agents generate code and configuration but **do not execute** anything. All outputs require human review before apply.
- Agents that read live infrastructure (deployment-validator) require read-only credentials scoped to the target environment.
- Never pass secrets as agent inputs. Reference secrets by name (e.g. `secret/prod/db-password`) — the agent will generate code that reads from the secrets manager, not embed the value.
- Agent outputs may contain resource names, IDs, and environment details. Treat outputs as internal-confidential.

---

## Contributing

Follow `CONTRIBUTING.md` at the repo root. For agent changes specifically:
1. Update the AGENT.md system prompt
2. Update the README.md if input/output contracts change
3. Update `example-input.md` to reflect the new behaviour
4. Test by running the agent against the example input and reviewing outputs against the relevant CLAUDE.md standards
