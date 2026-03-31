# API Scaffolder Agent

Generates an OpenAPI 3.1 spec, controller stubs, error types, and versioning docs for any REST API based on the organisation's API design standards. Enforces cursor pagination, RFC 9457 errors, idempotency keys, and consistent URL versioning out of the box.

## Prerequisites
- `standards/claude-md/api/CLAUDE.md` present.
- Relevant backend `CLAUDE.md` (`backend/java/` or `backend/dotnet/`).
- Claude Code CLI or Anthropic API access.

---

## Invocation Methods

### 1. Claude Code (interactive)
```bash
claude --agent agents/api-scaffolder/AGENT.md
# "Scaffold a Payments API with /payments and /refunds resources in Java,
#  OAuth2 JWT auth, idempotency on POST /payments"
```

### 2. Claude Code with file input
```bash
claude --agent agents/api-scaffolder/AGENT.md \
  --print \
  --input agents/api-scaffolder/example-input.md \
  > api/PaymentsAPI/generated.md
```

### 3. Anthropic API (Python)
```python
import anthropic
from pathlib import Path

client = anthropic.Anthropic(api_key="YOUR_API_KEY_HERE")

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=8096,
    system=Path("agents/api-scaffolder/AGENT.md").read_text(),
    messages=[{
        "role": "user",
        "content": Path("agents/api-scaffolder/example-input.md").read_text()
    }],
)
print(response.content[0].text)
```

### 4. GitHub Actions — scaffold on new feature branch
```yaml
name: Scaffold API

on:
  workflow_dispatch:
    inputs:
      api_name:
        required: true
      resources:
        required: true
        description: "Comma-separated, e.g. payments,refunds"
      backend_language:
        required: true
        default: java
      auth_type:
        default: oauth2-jwt

jobs:
  scaffold:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run API scaffolder
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/run_agent.py \
            --agent agents/api-scaffolder/AGENT.md \
            --api-name "${{ inputs.api_name }}" \
            --resources "${{ inputs.resources }}" \
            --backend-language "${{ inputs.backend_language }}" \
            --auth-type "${{ inputs.auth_type }}" \
            --output-dir "api/${{ inputs.api_name }}"

      - name: Raise PR
        run: |
          git checkout -b "scaffold/${{ inputs.api_name }}"
          git add api/
          git commit -m "feat: scaffold ${{ inputs.api_name }}"
          gh pr create --title "feat: scaffold ${{ inputs.api_name }}" \
            --body "Auto-scaffolded by api-scaffolder agent."
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `api_name` | string | Yes | PascalCase API name |
| `resources` | list | Yes | Plural resource names (e.g. `["payments","refunds"]`) |
| `backend_language` | enum | Yes | `java` or `dotnet` |
| `auth_type` | enum | Yes | `oauth2-jwt`, `api-key`, `mtls`, or `none` |
| `api_version` | string | No | Default `v1` |
| `base_package` | string | No | Root Java package or .NET namespace |
| `idempotent_resources` | list | No | Resources requiring `Idempotency-Key` header |
| `event_resources` | list | No | Resources that also emit domain events |

---

## Outputs

| File | Description |
|------|-------------|
| `openapi.yaml` | Complete OpenAPI 3.1 spec |
| `src/controllers/{Resource}Controller.*` | Controller stubs (one per resource) |
| `src/models/requests/Create{Resource}Request.*` | Request DTOs |
| `src/models/responses/{Resource}Response.*` | Response DTOs |
| `src/errors/ApiError.*` | RFC 9457 ProblemDetails type |
| `docs/VERSIONING.md` | Versioning policy |

---

## Standards Enforced

| Standard | Enforcement |
|----------|-------------|
| Cursor pagination | Offset/limit refused; only `cursor` + `limit` parameters |
| RFC 9457 errors | All 4xx/5xx reference `ProblemDetails` component |
| URL versioning | `/api/v{n}/` prefix; no `Accept` header versioning |
| Idempotency | `Idempotency-Key` header on requested POST/PATCH ops |
| Resource naming | Plural nouns, kebab-case, max 2 nesting levels |
| Security | Auth scheme from `auth_type` applied globally |

---

## After Scaffolding

1. Extract `openapi.yaml` and commit to the service repo.
2. Run `openapi-generator` to produce server stubs or client SDKs from the spec.
3. Implement service layer behind the generated controller interfaces.
4. Feed the spec into the `standards-reviewer` agent as part of PR review.
