# api-scaffolder Agent

Takes a high-level API specification and generates a complete, standards-compliant scaffold: OpenAPI 3.1 spec, controller/endpoint stubs, DTOs, validators, and use case ports. Enforces all standards from `standards/claude-md/api/CLAUDE.md` and the relevant backend standard.

---

## What It Produces

| Artefact | Description |
|---|---|
| `docs/api/openapi.yaml` | Complete OpenAPI 3.1 specification — the API contract |
| `src/api/{Resource}Controller.java` | Spring Boot `@RestController` with full annotations |
| `src/api/{Resource}Endpoints.cs` | ASP.NET Core Minimal API endpoint registration |
| `src/api/dto/` | Request/response DTOs (records with validation) |
| `src/api/Validators/` | FluentValidation validators (.NET) |
| `src/application/ports/I{Resource}Repository` | Repository port interface |
| `src/application/use-cases/` | Use case class stubs with correct signatures |

All code compiles. Stubs contain `// TODO: implement` with context.

---

## Inputs

| Field | Required | Description |
|---|---|---|
| `API_NAME` | Yes | Human-readable API name, e.g. `Orders API` |
| `SERVICE_NAME` | Yes | Service name for package/namespace root |
| `BASE_PATH` | Yes | URL base path, e.g. `/api/v1` |
| `LANGUAGE` | Yes | `java` or `dotnet` |
| `FRAMEWORK` | Yes | `springboot` or `aspnetcore` |
| `PACKAGE_BASE` | Yes | Root package (`com.acme.orders`) or namespace (`Acme.Orders`) |
| `RESOURCES` | Yes | List of resources with fields and operations |
| `SCOPES` | Yes | OAuth 2.0 scopes to declare |
| `ERROR_TYPES` | No | Custom error types to document in spec |

---

## How to Invoke

### Via Claude Code (interactive)

```bash
cat agents/api-scaffolder/example-input.md | claude agent run api-scaffolder
```

### Via Anthropic API

```python
import anthropic

with open("agents/api-scaffolder/AGENT.md") as f:
    system_prompt = f.read()

with open("agents/api-scaffolder/example-input.md") as f:
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

### Via GitHub Actions

```yaml
# .github/workflows/api-scaffold.yml
name: API Scaffold
on:
  workflow_dispatch:
    inputs:
      api_name:
        description: 'API name (e.g. Orders API)'
        required: true
      language:
        description: 'java or dotnet'
        required: true
        default: 'java'

jobs:
  scaffold:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate API scaffold
        uses: anthropics/claude-code-action@v1
        with:
          agent-system-prompt-file: agents/api-scaffolder/AGENT.md
          prompt: |
            API_NAME: ${{ inputs.api_name }}
            SERVICE_NAME: order-service
            BASE_PATH: /api/v1
            LANGUAGE: ${{ inputs.language }}
            FRAMEWORK: ${{ inputs.language == 'java' && 'springboot' || 'aspnetcore' }}
            PACKAGE_BASE: com.acme.orders
            RESOURCES:
              - name: Order
                plural: orders
                operations: [list, get, create, update, delete, confirm, cancel]
            SCOPES:
              - name: orders:read
                description: Read orders
              - name: orders:write
                description: Create and modify orders
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
      - uses: peter-evans/create-pull-request@v6
        with:
          title: "feat(api): scaffold ${{ inputs.api_name }}"
          branch: "feat/api-scaffold-${{ github.run_id }}"
```

---

## Composition

The api-scaffolder fits between infra-provisioner and app-deployer:

```
infra-provisioner → api-scaffolder → app-deployer → standards-reviewer
(infra modules)    (openapi + stubs)  (Dockerfile,    (validate generated
                                       K8s, CI/CD)     code before commit)
```

---

## Standards Enforced

| Standard | Source |
|---|---|
| API-first: spec before code | `api/CLAUDE.md` § API-First Design |
| Resource-oriented URL design | `api/CLAUDE.md` § REST Resource Design |
| RFC 9457 Problem Details errors | `api/CLAUDE.md` § Error Response Shape |
| URL versioning (`/api/v1/`) | `api/CLAUDE.md` § API Versioning |
| Cursor-based pagination | `api/CLAUDE.md` § Pagination |
| OAuth 2.0 Bearer security | `api/CLAUDE.md` § Authentication and Authorization |
| Constructor injection in controllers | `backend/java/CLAUDE.md` § Dependency Injection |
| Java records for DTOs | `backend/java/CLAUDE.md` § Use These Java Features |
| Minimal APIs with `IResult` | `backend/dotnet/CLAUDE.md` § ASP.NET Core Standards |
| FluentValidation | `backend/dotnet/CLAUDE.md` § CQRS with MediatR |
| IDs as strings, money as strings | `api/CLAUDE.md` § Timestamps and IDs |
