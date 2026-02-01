Title: Test Strategy

1. Objectives

Ensure correctness, reliability, and guard against regressions with a balanced test pyramid and measurable coverage targets.

2. Pyramid
- Unit tests: Fast, isolated; cover pure logic and small components.
- Integration tests: Exercise module boundaries and data stores.
- Contract tests: Validate external API clients against documented schemas.
- End-to-end (limited): Critical paths only; executed in CI nightly or pre-release.

3. Frameworks & tooling
- Java: JUnit 5, Mockito, Testcontainers (for DB/queue), JaCoCo coverage.
- Python: pytest, pytest-asyncio (if applicable), hypothesis (property-based), mypy strict mode for types.

4. Coverage expectations
- Changed files: ≥ 80% line coverage; branch coverage encouraged for critical paths.
- Critical modules: ≥ 90% line coverage; explicit justification required for exceptions.
- Reporting: JaCoCo XML/HTML; pytest `--cov` with term/HTML reports stored in CI artifacts.

5. Fixtures & test data
- Java: `@Testcontainers` for Postgres/Redis/Kafka; `src/test/resources` for seed data.
- Python: `pytest` fixtures for setup/teardown; factories for domain objects; deterministic seeds.

6. Mocks & doubles
- Prefer integration tests over excessive mocking.
- Mock external network calls; never call real third-party APIs in CI.
- Use spies for verifying interactions; avoid asserting private implementation details.

7. Performance & flakiness
- No sleeps; use time injection or fakes.
- Bound test runtime; parallelize where safe.
- Detect flaky tests; quarantine and fix promptly.

8. Example commands
- Java (Maven): `mvn -q -DskipTests=false clean test`
- Java (Gradle): `./gradlew test jacocoTestReport`
- Python (uv): `uv run pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing`
- Python (venv): `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=html`

9. Gatekeeping
- CI fails on coverage below threshold for changed modules.
- Lint/type gates: Checkstyle/Spotless, ruff/black/mypy must pass.
- Security scans: dependency checks; flag critical vulnerabilities.

10. Test data management
- Use anonymized synthetic data; no real PII.
- Ensure repeatability; clean up resources; idempotent setups.

