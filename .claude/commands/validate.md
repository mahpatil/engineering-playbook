<!-- // .claude/commands/validate.md -->
Validation pipeline:
Run static analysis, unit/integration tests, and a local smoke start using @EXECUTION_NOTES.md.
Python:
- If uv: `uv run pytest -q --maxfail=1 --disable-warnings`
- Else venv: create venv, install, run pytest with coverage
- Run static checks (ruff/flake8/black/mypy) if configured; fix and rerun
Java:
- If Maven: `mvn -q -DskipTests=false clean test` and ensure JaCoCo generates reports
- If Gradle: `./gradlew test` with coverage
- Enforce coverage thresholds on changed modules; increase tests if below target
Smoke:
- Start Python app minimally and run `scripts/smoke_check.py` or equivalent
- Package Java app and run `scripts/smoke_check.sh` (adjust paths)
Aggregate results with actionable remediation steps; fix issues and repeat until green.
Produce a validation summary (coverage deltas, performance notes, flake detection).
