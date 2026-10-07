# deployment-validator — Example Input (Static Mode)

## Invocation

Perform pre-promotion static manifest validation for the `order-service` deployment targeting the `staging` environment. This static scan evaluates rendered Kubernetes manifests (generated via Helm template or Kustomize build) against infrastructure and security standards in CI/CD before resources are applied to clusters.

The manifest stream below contains intentional violations across security, resilience, observability, and governance controls to demonstrate static gate enforcement and blocking on `exit 1`.

### Pre-Promotion Gate Execution

```bash
# Render multi-document YAML manifests from Helm chart
helm template order-service deploy/helm/order-service \
  --namespace order-service \
  -f deploy/helm/order-service/values-staging.yaml > /tmp/staged-manifest.yaml

# Execute static validation gate in CI/CD pipeline
agent run deployment-validator \
  --input agents/deployment-validator/example-input-static.md
```

---

## Request

```yaml
MODE: static
FAIL_LEVEL: HIGH
ENVIRONMENT: staging
CLOUD: gcp
SERVICE: order-service
PROJECT: acme-payments
DR_TIER: 1

MANIFEST: |
  ---
  apiVersion: v1
  kind: ServiceAccount
  metadata:
    name: order-service
    namespace: order-service
    labels:
      environment: staging
      project: acme-payments
      service: order-service
      managed-by: helm
    annotations:
      iam.gke.io/gcp-service-account: order-service-sa@acme-payments-staging.iam.gserviceaccount.com
  automountServiceAccountToken: false
  ---
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: staging-acme-payments-order-service
    namespace: order-service
    labels:
      app: order-service
      environment: staging
      project: acme-payments
      service: order-service
      managed-by: helm
  spec:
    replicas: 2
    selector:
      matchLabels:
        app: order-service
    template:
      metadata:
        labels:
          app: order-service
          environment: staging
          project: acme-payments
          service: order-service
        annotations:
          prometheus.io/scrape: "true"
          prometheus.io/port: "8080"
          prometheus.io/path: "/actuator/prometheus"
      spec:
        serviceAccountName: order-service
        terminationGracePeriodSeconds: 60
        securityContext:
          runAsNonRoot: false
          runAsUser: 0
          fsGroup: 2000
        containers:
          - name: order-service
            image: us-central1-docker.pkg.dev/acme-staging/services/order-service:latest
            imagePullPolicy: Always
            ports:
              - name: http
                containerPort: 8080
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: false
              capabilities:
                drop:
                  - ALL
            resources:
              requests:
                cpu: "250m"
                memory: "512Mi"
            livenessProbe:
              httpGet:
                path: /actuator/health/live
                port: 8080
              initialDelaySeconds: 30
              periodSeconds: 15
            env:
              - name: ENVIRONMENT
                value: "staging"
              - name: SPRING_PROFILES_ACTIVE
                value: "staging"
              - name: DB_PASSWORD
                value: "SuperSecretStagingPassword123!"
  ---
  apiVersion: v1
  kind: Service
  metadata:
    name: staging-acme-payments-order-service
    namespace: order-service
    labels:
      app: order-service
      environment: staging
      project: acme-payments
      service: order-service
      managed-by: helm
  spec:
    type: ClusterIP
    ports:
      - name: http
        port: 8080
        targetPort: 8080
    selector:
      app: order-service
```

---

## Violations in This Manifest Stream

The multi-document manifest stream contains intentional violations across multiple control categories:

### Security (SEC)

- `SEC-001` (CRITICAL): `spec.template.spec.securityContext.runAsNonRoot` is set to `false`.
- `SEC-002` (HIGH): `spec.template.spec.securityContext.runAsUser` is set to `0` (root).
- `SEC-004` (HIGH): `readOnlyRootFilesystem` is set to `false` in container `securityContext`.
- `SEC-010` (HIGH): Container image uses floating tag `:latest` instead of immutable SHA256 digest or semver.
- `SEC-014` (CRITICAL): `DB_PASSWORD` environment variable is defined as a plaintext literal instead of sourcing from Kubernetes Secret or ExternalSecret.

### Network (NET)

- `NET-001` (HIGH): No `NetworkPolicy` resource defined in the namespace manifest stream.
- `NET-002` (HIGH): Default deny-all ingress policy missing from manifest stream.
- `NET-003` (HIGH): Default deny-all egress policy missing from manifest stream.

### Resilience (RES)

- `RES-001` (HIGH): No `PodDisruptionBudget` resource defined in the manifest stream.
- `RES-002` (HIGH): Missing minimum availability configuration via PDB.
- `RES-006` (HIGH): Container `resources.limits` block is completely missing (memory limit required).

### Observability (OBS)

- `OBS-002` (HIGH): Missing `readinessProbe` configuration on `order-service` container (`livenessProbe` is configured).

### Tagging & Governance (TAG)

- `TAG-004` (LOW): Missing mandatory label `team` on Deployment `metadata.labels`.
- `TAG-005` (LOW): Missing mandatory label `cost-centre` on Deployment `metadata.labels`.

### Disaster Recovery & Backups (DR)

- `DR-001` through `DR-006` (N/A): Evaluates to `N/A` in `MODE: static` because no database resource manifests are present in the stream.

---

## Expected Verdict

- **Overall Result:** `NON-COMPLIANT`
- **Exit Code:** `1` (blocked at CI gate because multiple violations have severity `>= HIGH`, meeting `FAIL_LEVEL: HIGH`)
- **Remediation Required:** Remediate `CRITICAL` and `HIGH` findings in Helm chart / Kustomize template before re-running pre-promotion static validation.
