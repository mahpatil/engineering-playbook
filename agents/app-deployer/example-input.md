# app-deployer — Example Input

## Invocation

Generate a full deployment artefact set for the Java Spring Boot order-service targeting GCP/GKE with progressive canary delivery, isolated database migrations, smoke testing, and supply chain security.

---

## Request

```yaml
APP_NAME: order-service
PROJECT: acme-payments
TEAM: payments-platform
LANGUAGE: java
FRAMEWORK: springboot
CONTAINER_REGISTRY: us-central1-docker.pkg.dev/acme-prod/services
CLUSTER_NAME: prod-acme-payments-order-service-gke-cluster
NAMESPACE: order-service
ENVIRONMENTS: [dev, staging, prod]
PORT: 8080
HEALTH_PATH: /actuator
METRICS_PATH: /actuator/prometheus
DR_TIER: 1
DEPLOYMENT_STRATEGY: canary
PROGRESSIVE_DELIVERY_TOOL: argo-rollouts
DATABASE_MIGRATION:
  enabled: true
  engine: flyway
  image: us-central1-docker.pkg.dev/acme-prod/services/order-service-migrations:1.4.2
SUPPLY_CHAIN_SECURITY:
  cosign_signing: true
  slsa_provenance: true
REPLICAS:
  dev: 1
  staging: 2
  prod: 3
RESOURCES:
  requests:
    cpu: "250m"
    memory: "512Mi"
  limits:
    cpu: "1000m"
    memory: "1Gi"
DEPENDENCIES:
  - name: payments-gateway
    namespace: payments-gateway
    port: 8080
  - name: customer-service
    namespace: customer-service
    port: 8080
```

---

## Context

The order-service is a Spring Boot 3.4 application built with Gradle. It exposes a REST API on port 8080 and uses:

- Spring Boot Actuator for health (`/actuator/health/live`, `/actuator/health/ready`) and Prometheus metrics (`/actuator/prometheus`)
- Flyway for relational schema migrations preceding application pod creation
- Argo Rollouts for canary deployments with automated PromQL metric rollback (Tier 1 revenue-critical path)
- GCP Secret Manager credentials via External Secrets Operator and Workload Identity
- Sigstore Cosign keyless signing and SLSA Level 3 build provenance

---

## Expected Output

### Dockerfile

- Multi-stage build: `eclipse-temurin:21-jdk-alpine` builder, `gcr.io/distroless/java21-debian12` runtime
- Non-root `USER 65534:65534`, port 8080 exposed, entrypoint `["java", "-jar", "/app/app.jar"]`

### Kubernetes & Progressive Delivery (Helm)

- `rollout.yaml`: Argo Rollouts CRD with canary steps (5% -> 25% -> 50% -> 100%), securityContext, health probes
- `analysistemplate.yaml`: PromQL metric templates checking 5xx error rate (< 0.1%) and P99 latency (<= 1.15x baseline)
- `job-migration.yaml`: Pre-upgrade Helm hook Job running Flyway (`activeDeadlineSeconds: 300`, `backoffLimit: 1`)
- `hpa.yaml`: minReplicas=3, maxReplicas=15, CPU 70%, memory 80%
- `pdb.yaml`: minAvailable=2 (Tier 1 prod)
- `networkpolicy.yaml`: default deny ingress, allow ingress controller and prometheus, allow dependencies and kube-dns
- `externalsecret.yaml` & `serviceaccount.yaml`: Secret Manager mapping and GKE Workload Identity binding

### Smoke Test Harness

- `tests/smoke/smoke-test.sh`: Bash test harness checking health endpoints, latency (< 500ms), and synthetic routes

### GitHub Actions CI/CD

- `ci.yml`: lint -> unit test -> static check (`deployment-validator --mode=static`) -> build -> trivy scan -> Cosign sign -> SLSA provenance
- `cd-dev.yml`: auto-deploy to dev namespace on main merge
- `cd-staging.yml`: auto-deploy to staging with post-deploy smoke test step
- `cd-prod.yml`: manual approval gate, progressive canary rollout with automated metric analysis, and smoke verification
