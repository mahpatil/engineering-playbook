# Claude Agent Suite — Infrastructure & Application Deployment

A collection of reusable Claude agents that help enterprise engineers provision infrastructure, deploy applications, scaffold APIs, and continuously enforce engineering standards. Each agent is grounded in the organisation's CLAUDE.md standards living under `standards/claude-md/`.

---

## Who This Is For

| Role | Agents you'll use most |
|------|----------------------|
| Platform / DevOps engineers | `infra-provisioner`, `app-deployer`, `deployment-validator` |
| Backend engineers | `api-scaffolder`, `standards-reviewer` |
| Tech leads / architects | `standards-reviewer`, `deployment-validator` |
| Security & compliance teams | `deployment-validator`, `standards-reviewer` |

---

## Quick-Start Table

| Agent | When to trigger | Key inputs | Key outputs |
|-------|----------------|-----------|-------------|
| [infra-provisioner](./infra-provisioner/) | New environment needed | app name, cloud, env, DR tier | Terraform module (`main.tf`, `variables.tf`, `outputs.tf`, `backend.tf`) |
| [app-deployer](./app-deployer/) | New service ready to ship | repo name, app type, env, registry | Dockerfile, K8s manifests, Helm chart, GitHub Actions pipeline |
| [api-scaffolder](./api-scaffolder/) | New API being designed | API name, resources, language, auth | OpenAPI 3.1 spec, controller stubs, RFC 9457 error types |
| [standards-reviewer](./standards-reviewer/) | PR opened / pre-commit | PR diff or directory, scope | Findings table (CRITICAL→LOW) + remediation summary |
| [deployment-validator](./deployment-validator/) | Pre-deploy gate or weekly audit | kubectl output or manifest files, env | Pass/fail compliance report + remediation plan |

---

## How Agents Compose

### Pipeline 1: Provision → Deploy (new service)

```
┌─────────────────────┐       ┌─────────────────────┐
│  infra-provisioner  │──────▶│    app-deployer     │
│                     │       │                     │
│  Outputs:           │       │  Uses:              │
│  - k8s cluster      │       │  - cluster endpoint │
│  - image registry   │       │  - registry URL     │
│  - namespace        │       │  - namespace        │
└─────────────────────┘       └─────────────────────┘
         │
         ▼
  Review & apply Terraform
  (platform engineer gate)
```

**Step 1** — Run `infra-provisioner` with your app name and cloud target. Review the generated Terraform, apply it, and capture the outputs (cluster endpoint, registry URL, namespace).

**Step 2** — Pass those outputs as inputs to `app-deployer`. It generates the Dockerfile, Kubernetes manifests, Helm chart, and CI/CD pipeline wired to the exact registry and cluster from Step 1.

**Step 3** — Merge the generated artefacts. The generated GitHub Actions pipeline handles all subsequent builds and deployments automatically.

---

### Pipeline 2: Scaffold → Review → Ship (new API)

```
┌─────────────────────┐       ┌─────────────────────┐
│   api-scaffolder    │──────▶│  standards-reviewer │
│                     │       │                     │
│  Outputs:           │       │  Checks:            │
│  - openapi.yaml     │       │  - cursor pagination│
│  - controller stubs │       │  - RFC 9457 errors  │
│  - error types      │       │  - versioning       │
└─────────────────────┘       └─────────────────────┘
                                        │
                                        ▼
                              Fix findings → merge
```

**Step 1** — Run `api-scaffolder` to generate the OpenAPI spec and server stubs.

**Step 2** — Pipe the output into `standards-reviewer` (scope: `api` + the relevant backend scope) to verify compliance before committing.

**Step 3** — Implement business logic behind the generated controller interfaces. The spec is the contract.

---

### Pipeline 3: PR Guard (ongoing)

```
Every PR  ──▶  standards-reviewer  ──▶  PASS / FAIL
                    (GitHub Actions)
                          │
            FAIL? ──▶  block merge
            PASS? ──▶  continue to deploy gate
                          │
              deploy-staging merged ──▶  deployment-validator
                                              (post-deploy)
```

Configure `standards-reviewer` as a required GitHub Actions check on `main`. Configure `deployment-validator` as a scheduled weekly audit or a post-deploy check.

---

## How Standards Fit In

All agents read from `standards/claude-md/` at runtime. This means:

- **Updating a standard** automatically updates what the agents enforce — no agent code changes needed.
- **Adding a new standard** (e.g. `standards/claude-md/data/CLAUDE.md`) can be adopted by adding a new scope to `standards-reviewer`.
- Agents halt and tell you if a required standard file is missing — they don't silently generate non-compliant output.

---

## How to Fork and Extend for Your Org

1. **Add your tagging taxonomy** — update the mandatory tags list in `standards/claude-md/infra/CLAUDE.md`. All agents referencing it will pick up the change automatically.

2. **Add a new language standard** — create `standards/claude-md/backend/golang/CLAUDE.md`. Update `app-deployer/AGENT.md` and `api-scaffolder/AGENT.md` to reference it when `app_type=go` is passed.

3. **Add a new cloud provider** — extend the cloud-specific sections in `infra-provisioner/AGENT.md` and `deployment-validator/AGENT.md`.

4. **Add a new check to the validator** — add a row to the check table in `deployment-validator/AGENT.md`. No code changes needed.

5. **Tighten the PR gate** — change the GitHub Actions step in `standards-reviewer/README.md` to also fail on MEDIUM findings in `prod`-targeted PRs.

6. **Swap the model** — all agents use `claude-opus-4-6` in the API examples. Replace with `claude-sonnet-4-6` for faster, cheaper runs in pre-commit or CI contexts where ultra-high quality is less critical.

---

## Directory Structure

```
agents/
├── README.md                          # This file
├── infra-provisioner/
│   ├── AGENT.md                       # System prompt
│   ├── README.md                      # Invocation guide
│   └── example-input.md               # Realistic worked example
├── app-deployer/
│   ├── AGENT.md
│   ├── README.md
│   └── example-input.md
├── api-scaffolder/
│   ├── AGENT.md
│   ├── README.md
│   └── example-input.md
├── standards-reviewer/
│   ├── AGENT.md
│   ├── README.md
│   └── example-input.md               # Diff with deliberate violations
└── deployment-validator/
    ├── AGENT.md
    ├── README.md
    └── example-input.md               # Namespace audit with known failures
```

---

## Related

- `standards/claude-md/` — The CLAUDE.md standards files that agents read at runtime (see PR #1).
- `standards/detailed/` — Detailed narrative standards documents.
- `standards/overall/` — Principles, patterns, tech-stack choices, and checklists.
