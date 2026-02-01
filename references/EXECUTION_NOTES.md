Title: Execution Notes

1. Local setup

- Java (Maven):

 ▫ ‎`mvn -q -DskipTests=false clean test`

 ▫ ‎`mvn -q clean package`

 ▫ Run: ‎`java -jar target/api.jar` (adjust artifact name)

- Java (Gradle):

 ▫ ‎`./gradlew test`

 ▫ ‎`./gradlew build`

 ▫ Run: ‎`java -jar build/libs/api.jar`

- Python (uv):

 ▫ ‎`uv sync`

 ▫ Run worker: ‎`uv run python -m worker.main`

- Python (venv):

 ▫ ‎`python -m venv .venv && source .venv/bin/activate`

 ▫ ‎`pip install -r requirements.txt`

 ▫ Run worker: ‎`python -m worker.main`

2. Environment variables

- Shared: ‎`DB_URL`, ‎`DB_USER`, ‎`DB_PASS`, ‎`REDIS_URL`, ‎`BROKER_URL`, ‎`LOG_LEVEL`

- Java: ‎`JAVA_OPTS`, ‎`SPRING_PROFILES_ACTIVE`

- Python: ‎`PYTHONUNBUFFERED=1`, ‎`APP_ENV`

- Secrets are injected via environment or secret manager; never committed.

3. Seeds/fixtures

- Java: ‎`src/test/resources/data/*.sql` for integration seeds.

- Python: ‎`tests/fixtures/*.json` for unit and integration tests.

4. Smoke checks

- Java API: ‎`curl -f http://localhost:8080/health`

- Python worker: enqueue test message; assert processing and metrics increment.

5. CI pipeline (outline)

- Checkout, setup JDK 21, setup Python 3.12.

- Install dependencies (Maven/Gradle; uv/venv).

- Run tests and coverage (JaCoCo/pytest).

- Build artifacts; run smoke scripts.

- On success: run automation (Claude Code commands) to validate and raise PR.

6. Observability in dev

- Enable verbose logging; local metrics via Prometheus on ‎`:9090`; traces via OpenTelemetry.

7. Troubleshooting

- Port conflicts: verify services on 8080/9090; adjust via env.

- Dependency issues: clear caches (‎`~/.m2/repository`, ‎`~/.gradle/caches`, ‎`.venv`/‎`.uv`).

