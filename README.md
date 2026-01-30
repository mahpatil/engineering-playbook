# Pre-requisites

1. Install Claude Code (CLI)
2. Log in and setup claude code
3. Run it from your project root so it can read/write the repo.
4. Ensure the repo is clean and under Git; Claude uses diffs/commits and PR metadata.
5. Create the following:

- STYLE_GUIDE.md — linting rules, naming, formatting, doc standards, examples
- PRINCIPLES.md — design tenets, tradeoffs, security/privacy constraints, performance targets
- ARCHITECTURE.md — modules, data flow, patterns, dependencies, service boundaries
- REQUIREMENTS.md — user stories, acceptance criteria, edge cases, non-functional requirements
- EXECUTION_NOTES.md — how to run the app locally and in CI, env vars, seeds/fixtures
- TEST_STRATEGY.md — test pyramid, frameworks, coverage expectations, fixtures, mocks
- PR_TEMPLATES/ — your PR checklist and sections

6. Copy project-level commands in .claude/commands so anyone (and CI) can invoke standardized workflows without typing long instructions
7. Create specialised sub agents: Subagents let Claude delegate tasks to focused roles (e.g., code-reviewer, tester, PR author) and run them in parallel. ​

# GitHub actions

```yaml
# .github/workflows/claude.yml
# .github/workflows/claude-gradle-uv.yml
name: Claude Automation (Gradle + uv)
on:
  workflow_dispatch:
  push:
    branches: [ feature/* ]
jobs:
  build-validate-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.local/bin" >> $GITHUB_PATH
      - name: Python deps via uv
        run: |
          uv sync

      - name: Set up Java (Gradle)
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '21'
      - name: Gradle validate
        run: |
          chmod +x gradlew || true
          ./gradlew test

      - name: Python validate
        run: |
          uv run pytest -q --maxfail=1 --disable-warnings || true

      - name: Initialize with guides
        run: claude /initialize --output-format text

      - name: Implement feature
        env:
          FEATURE: "${{ github.ref_name }}"
        run: claude /implement "$FEATURE" --output-format text

      - name: Validate
        run: claude /validate --output-format text

      - name: Raise PR
        if: success()
        run: claude /raise-pr --output-format text

```

# How this works
1. Initialize against STYLE_GUIDE/PRINCIPLES/ARCHITECTURE and align tooling.
2. Implement the requested feature from REQUIREMENTS.md (or a branch name/ticket).
3. Validate via tests, static analysis, and smoke run; remediate until green.
4. Raise a PR with a complete, templatized description and evidence.

One-command local runs
- Python venv: `source .venv/bin/activate && claude /implement "feature-123" && claude /validate && claude /raise-pr`
- Python uv: `uv run claude /implement "feature-123"`
- Maven: `mvn -q -DskipTests=false clean test && claude /validate && claude /raise-pr`
- Gradle: `./gradlew test && claude /validate && claude /raise-pr`

Security notes
- Do not store secrets in repo or Claude command files. Use CI secrets and `.env` locally excluded by `.gitignore`.
- Auto-accept mode should run in isolated environments and safe whitelisted directories.
- Keep explicit allowedCommands minimal to reduce blast radius.

