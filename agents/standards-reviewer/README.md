# standards-reviewer Agent

Reviews a PR diff or set of files against the full CLAUDE.md standards suite, producing structured findings with severity, citations, and remediations. Designed to run as a PR gate in CI.

---

## What It Produces

A structured review report containing:

| Section | Description |
|---|---|
| **Summary** | Overall compliance posture and finding counts |
| **Findings** | Each violation with file:line, standard citation, severity, before/after code |
| **Verdict** | `BLOCK` / `WARN` / `PASS` with justification |
| **Positive Observations** | What was done well |

### Severity Levels

| Severity | Meaning | CI Action |
|---|---|---|
| `CRITICAL` | Security vulnerability, secret exposure, data loss risk | Block merge |
| `HIGH` | Architecture violation, missing security control, error shape leaking internals | Block merge |
| `MEDIUM` | Standards deviation with functional impact | Warn |
| `LOW` | Standards deviation without immediate functional impact | Warn |
| `INFO` | Improvement beyond standards minimum | Informational |

---

## Inputs

**Git diff:**
```
REVIEW_TYPE: diff
LANGUAGE: java
CONTEXT: Adding order confirmation endpoint
DIFF:
<git diff output>
```

**File set:**
```
REVIEW_TYPE: files
LANGUAGE: dotnet
FILES:
--- src/Payments/Api/PaymentsEndpoints.cs ---
<file contents>
```

---

## How to Invoke

### Via Claude Code (interactive)

```bash
git diff HEAD~1 | claude agent run standards-reviewer
```

### As a GitHub Actions PR Gate

```yaml
# .github/workflows/standards-review.yml
name: Standards Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  standards-review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get PR diff
        run: git diff origin/${{ github.base_ref }}...HEAD > pr.diff

      - name: Run standards review
        id: review
        uses: anthropics/claude-code-action@v1
        with:
          agent-system-prompt-file: agents/standards-reviewer/AGENT.md
          prompt: |
            REVIEW_TYPE: diff
            LANGUAGE: mixed
            CONTEXT: ${{ github.event.pull_request.title }}
            DIFF:
            $(cat pr.diff)
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Post review as PR comment
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Standards Review\n\n${process.env.REVIEW_OUTPUT}`
            })
        env:
          REVIEW_OUTPUT: ${{ steps.review.outputs.result }}

      - name: Block on BLOCK verdict
        run: |
          if echo "${{ steps.review.outputs.result }}" | grep -q "**BLOCK**"; then
            echo "Standards review returned BLOCK verdict. Fix violations before merging."
            exit 1
          fi
```

### Via Anthropic API

```python
import anthropic
import subprocess

def review_pr(pr_diff: str, context: str = "") -> dict:
    with open("agents/standards-reviewer/AGENT.md") as f:
        system_prompt = f.read()

    prompt = f"""REVIEW_TYPE: diff
LANGUAGE: mixed
CONTEXT: {context}

DIFF:
{pr_diff}"""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}]
    )

    review_text = message.content[0].text
    verdict = "BLOCK" if "**BLOCK**" in review_text else \
              "WARN"  if "**WARN**"  in review_text else "PASS"

    return {"verdict": verdict, "review": review_text}

diff = subprocess.check_output(["git", "diff", "origin/main...HEAD"]).decode()
result = review_pr(diff, context="Adding Stripe payment integration")

if result["verdict"] == "BLOCK":
    raise SystemExit(1)
```

---

## What the Agent Checks

| Category | Examples |
|---|---|
| Security | Secrets in code, SQL injection, missing auth, PII in logs, credentials in URLs |
| Architecture | Layer violations, business logic in controllers |
| Error Handling | Swallowed exceptions, stack traces in responses, wrong status codes |
| Observability | Unstructured logs, no correlation ID, no circuit breaker |
| Testing | `Thread.sleep`, shared state, H2 instead of Testcontainers |
| API Design | Verbs in URLs, integer IDs, floats for money, wrong status codes |
| Infrastructure | Missing tags, public endpoints, hardcoded secrets |
| Frontend | XSS risks, `any` type, missing a11y, empty states |

---

## Composition

Run standards-reviewer as both a PR gate and to validate generated output from other agents:

```
api-scaffolder output → standards-reviewer  (validate generated code)
developer PR         → standards-reviewer  (ongoing gate)
```
