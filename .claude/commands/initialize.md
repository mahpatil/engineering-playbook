<!-- // .claude/commands/initialize.md -->
Read and internalize @STYLE_GUIDE.md, @PRINCIPLES.md, @ARCHITECTURE.md, @TEST_STRATEGY.md.
Verify tooling is aligned: configure linters/formatters, type-checkers, test runner.
Report planned changes needed to meet STYLE_GUIDE and PRINCIPLES. Then apply them.
Ensure the dev environment matches @EXECUTION_NOTES.md; fix drift as required.
Produce and apply a minimal plan that brings tooling and configs up to standards.
For Python:
- Ensure uv or venv setup is consistent with @EXECUTION_NOTES.md
- Align lint/format (ruff/flake8/black/mypy as applicable) and fix style drift
For Java:
- Ensure Maven or Gradle configs are aligned with @PRINCIPLES.md and @TEST_STRATEGY.md
- Add/align JaCoCo coverage and JUnit 5 setup; fix style drift (Spotless/Checkstyle)
