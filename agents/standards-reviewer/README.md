# Standards Reviewer Agent

Performs automated compliance reviews of PR diffs or source directories against the organisation's engineering standards. Produces a structured findings table with severity (CRITICAL/HIGH/MEDIUM/LOW), file+line references, the specific standard violated, and a remediation suggestion.

## Prerequisites
- One or more `standards/claude-md/*/CLAUDE.md` files present.
- Claude Code CLI or Anthropic API access.

---

## Invocation Methods

### 1. Claude Code — interactive PR review
```bash
# Pipe a PR diff and review against all standards
gh pr diff 42 | claude --agent agents/standards-reviewer/AGENT.md \
  --message "Review this diff against all standards. PR: https://github.com/acme/payments-api/pull/42"
```

### 2. Claude Code — directory review
```bash
claude --agent agents/standards-reviewer/AGENT.md \
  --message "Review the src/ directory for backend-java standards compliance"
```

### 3. Pre-commit hook
Add to `.git/hooks/pre-commit` (or use `pre-commit` framework):

```bash
#!/usr/bin/env bash
set -euo pipefail

DIFF=$(git diff --cached)
if [ -z "$DIFF" ]; then exit 0; fi

RESULT=$(echo "$DIFF" | claude --agent agents/standards-reviewer/AGENT.md \
  --print \
  --message "Review this staged diff. standards_scope=all. Fail on any CRITICAL or HIGH findings.")

echo "$RESULT"

# Fail commit if CRITICAL or HIGH findings exist
if echo "$RESULT" | grep -qE '^\| [0-9]+ \| (CRITICAL|HIGH)'; then
  echo ""
  echo "ERROR: Standards review found CRITICAL or HIGH violations. Fix before committing."
  exit 1
fi
```

### 4. GitHub Actions — PR check
```yaml
# .github/workflows/standards-review.yml
name: Standards Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get PR diff
        id: diff
        run: |
          git diff origin/${{ github.base_ref }}...HEAD > pr.diff
          echo "diff_size=$(wc -c < pr.diff)" >> "$GITHUB_OUTPUT"

      - name: Run standards review
        if: steps.diff.outputs.diff_size > 0
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/run_agent.py \
            --agent agents/standards-reviewer/AGENT.md \
            --input pr.diff \
            --input-type pr-diff \
            --standards-scope all \
            --pr-url "https://github.com/${{ github.repository }}/pull/${{ github.event.pull_request.number }}" \
            --author "${{ github.event.pull_request.user.login }}" \
            > review-report.md

      - name: Post review as PR comment
        if: always()
        run: |
          gh pr comment ${{ github.event.pull_request.number }} \
            --body "$(cat review-report.md)"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Fail on CRITICAL/HIGH findings
        run: |
          if grep -qE '^\| [0-9]+ \| (CRITICAL|HIGH)' review-report.md; then
            echo "::error::Standards review found CRITICAL or HIGH violations."
            exit 1
          fi
```

---

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `input_type` | enum | Yes | `pr-diff` or `directory` |
| `content` | string | Yes | The diff text or directory listing |
| `standards_scope` | enum | Yes | `infra`, `backend-java`, `backend-dotnet`, `api`, `frontend`, or `all` |
| `pr_url` | string | No | For report context |
| `author` | string | No | For report context |
| `base_branch` | string | No | Default `main` |

---

## Output

The agent produces a Markdown report with:

1. **Report header** — metadata, date, finding counts.
2. **Findings table** — severity, file, line, standard, description, remediation.
3. **Summary** — grouped by severity; passed checks listed.

---

## Severity Levels

| Severity | Policy | Action |
|----------|--------|--------|
| CRITICAL | Security, compliance failure | Block merge |
| HIGH | Mandatory standard violated | Block merge |
| MEDIUM | Recommended standard violated | Reviewer discretion |
| LOW | Style / convention | Advisory |

---

## Composing with Other Agents

- Run `api-scaffolder` to generate code, then pipe the output straight into `standards-reviewer` to verify it before committing.
- Run `standards-reviewer` on `infra-provisioner` output before applying Terraform.
- Configure the GitHub Actions example above as a required status check on protected branches.
