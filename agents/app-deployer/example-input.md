# app-deployer — Example Input

## Invocation

Generate a full deployment artefact set for the Java Spring Boot order-service targeting GCP/GKE.

---

## Request

```
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
- Virtual threads (Java 21) for high-concurrency request handling
- OpenTelemetry Java agent for distributed tracing (injected via environment variable at runtime)
- Reads DB credentials and Redis auth from GCP Secret Manager via External Secrets Operator

The service must tolerate rolling deployments with zero downtime (Tier 1, revenue-critical path).

---

## Expected Output

### Dockerfile

A multi-stage Dockerfile that:
- Stage 1 (`builder`): `eclipse-temurin:21-jdk-alpine`, runs `./gradlew bootJar`
- Stage 2 (`runtime`): `gcr.io/distroless/java21-debian12`, copies the fat JAR
- Sets `USER 65534:65534`
- Exposes port 8080
- Uses `ENTRYPOINT ["java", "-jar", "/app/app.jar"]`

### Kubernetes Manifests (Helm)

- `deployment.yaml`: 3 replicas (prod), all security context fields, readiness/liveness on `/actuator/health/ready` and `/actuator/health/live`, preStop sleep 5, terminationGracePeriodSeconds 60, Prometheus annotations, OTel agent env var
- `hpa.yaml`: minReplicas=3, maxReplicas=15, CPU 70%, memory 80%
- `pdb.yaml`: minAvailable=2 (Tier 1 prod)
- `networkpolicy.yaml`: deny all ingress, allow from ingress-nginx on 8080, allow from prometheus on 8080, allow egress to payments-gateway:8080 and customer-service:8080, allow egress to kube-dns:53
- `externalsecret.yaml`: reads `order-service-db-password` and `order-service-redis-auth` from GCP Secret Manager via External Secrets Operator
- `serviceaccount.yaml`: `automountServiceAccountToken: false`, annotated with GKE workload identity

### GitHub Actions

- `ci.yml`: checkout → setup Java 21 → Gradle build + test → trivy image scan (block HIGH+) → push to Artifact Registry on main
- `cd-dev.yml`: auto-deploy on ci.yml success on main, helm upgrade --install to dev namespace
- `cd-staging.yml`: auto-deploy after cd-dev success, with smoke test step
- `cd-prod.yml`: `environment: production` with manual approval, helm upgrade to prod, post-deploy health check
