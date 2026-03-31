# Example Input: Deploy payments-api to Staging on GKE

## Request

Deploy the `payments-api` Java Spring Boot service to the staging environment on Google Kubernetes Engine.

## Parameters

| Field | Value |
|-------|-------|
| `repo_name` | `payments-api` |
| `app_type` | `java-spring-boot` |
| `target_env` | `staging` |
| `image_registry` | `us-central1-docker.pkg.dev/acme-project/apps` |
| `k8s_namespace` | `payments-staging` |
| `port` | `8080` |
| `java_version` | `21` |
| `min_replicas` | `1` |
| `max_replicas` | `5` |

## Context

The `payments-api` service:
- Is built with Gradle (`./gradlew bootJar`).
- Exposes Spring Boot Actuator at `/actuator/health` and `/actuator/health/readiness`.
- Requires read access to GCP Secret Manager paths `projects/acme-project/secrets/payments-api-*` at runtime (via Workload Identity — no static credentials in the image).
- Connects to a Cloud SQL PostgreSQL instance via the Cloud SQL Auth Proxy sidecar.
- Must not be reachable from the public internet — ingress only via the internal GKE ingress controller.

## Expected Output

### Dockerfile
- Two-stage build: `eclipse-temurin:21-jdk-alpine` → `eclipse-temurin:21-jre-alpine`.
- Final image runs as uid 1000 (`appuser`).
- `HEALTHCHECK` using `/actuator/health`.
- No `latest` tag on any `FROM`.

### Kubernetes Manifests (`k8s/`)
- `namespace.yaml` — namespace `payments-staging` with labels `env=staging`, `team=payments-platform`.
- `deployment.yaml` — 1 replica initially, Cloud SQL Auth Proxy as a sidecar container, readiness probe on `/actuator/health/readiness` with 10s initial delay, `readOnlyRootFilesystem: true`, `runAsNonRoot: true`, resource limits as per staging tier.
- `service.yaml` — ClusterIP on port 8080.
- `hpa.yaml` — min 1, max 5 replicas, CPU target 70%.
- `networkpolicy.yaml` — deny all ingress except from `ingress-nginx` namespace; deny all egress except kube-dns (UDP 53) and the Cloud SQL Auth Proxy port 5432.

### Helm Chart (`helm/`)
- `Chart.yaml` — name `payments-api`, version `0.1.0`.
- `values.yaml` — image repository, tag as `latest` placeholder (overridden in pipeline to SHA), replica count, port.
- `values-staging.yaml` — `replicaCount: 1`, resource overrides for staging tier.
- `values-prod.yaml` — `replicaCount: 2`, resource overrides for prod tier, topologySpreadConstraints enabled.

### GitHub Actions Pipeline (`.github/workflows/ci-cd.yml`)
Stages:
1. `build` — `./gradlew bootJar -x test` then `./gradlew test`.
2. `security-scan` — Trivy on the built image; SARIF upload; fail on CRITICAL/HIGH.
3. `push` — `docker/login-action` with `${{ secrets.REGISTRY_TOKEN }}`; push image tagged `${{ github.sha }}`.
4. `deploy-staging` — `helm upgrade --install` to `payments-staging` namespace; only on `main` branch.
5. `deploy-prod` — same, `payments-prod` namespace; requires manual approval via `environment: production`.

## What This Should NOT Contain
- `latest` image tags in any manifest or pipeline step.
- `runAsRoot: true` or `allowPrivilegeEscalation: true`.
- Hard-coded registry credentials or service account keys.
- Missing `resources` limits on any container (including the Cloud SQL proxy sidecar).
