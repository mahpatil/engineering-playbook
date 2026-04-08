# deployment-validator — Example Input

## Invocation

Audit the production order-service deployment for compliance with infra/CLAUDE.md standards. The evidence below contains intentional violations for demonstration purposes.

---

## Request

```
ENVIRONMENT: prod
CLOUD: gcp
SERVICE: order-service
PROJECT: acme-payments
DR_TIER: 1

EVIDENCE:
  - type: kubectl_get_deployments
    content: |
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: order-service
        namespace: order-service
        labels:
          app: order-service
          environment: prod
      spec:
        replicas: 3
        selector:
          matchLabels:
            app: order-service
        template:
          metadata:
            labels:
              app: order-service
              environment: prod
            annotations:
              prometheus.io/scrape: "true"
              prometheus.io/port: "8080"
              prometheus.io/path: "/actuator/prometheus"
          spec:
            serviceAccountName: order-service
            terminationGracePeriodSeconds: 60
            containers:
              - name: order-service
                image: us-central1-docker.pkg.dev/acme-prod/services/order-service:latest
                ports:
                  - containerPort: 8080
                resources:
                  requests:
                    cpu: "250m"
                    memory: "512Mi"
                  limits:
                    cpu: "1000m"
                    memory: "1Gi"
                livenessProbe:
                  httpGet:
                    path: /actuator/health/live
                    port: 8080
                  initialDelaySeconds: 30
                  periodSeconds: 15
                readinessProbe:
                  httpGet:
                    path: /actuator/health/ready
                    port: 8080
                  initialDelaySeconds: 10
                  periodSeconds: 10
                env:
                  - name: SPRING_PROFILES_ACTIVE
                    value: "prod"
                  - name: DB_PASSWORD
                    value: "SuperSecret123!"

  - type: kubectl_get_networkpolicy
    content: |
      # No NetworkPolicy resources found in namespace order-service

  - type: kubectl_get_hpa
    content: |
      apiVersion: autoscaling/v2
      kind: HorizontalPodAutoscaler
      metadata:
        name: order-service
        namespace: order-service
      spec:
        scaleTargetRef:
          apiVersion: apps/v1
          kind: Deployment
          name: order-service
        minReplicas: 3
        maxReplicas: 15
        metrics:
          - type: Resource
            resource:
              name: cpu
              target:
                type: Utilization
                averageUtilization: 70

  - type: kubectl_get_pdb
    content: |
      # No PodDisruptionBudget resources found in namespace order-service

  - type: kubectl_get_serviceaccounts
    content: |
      apiVersion: v1
      kind: ServiceAccount
      metadata:
        name: order-service
        namespace: order-service
        annotations:
          iam.gke.io/gcp-service-account: order-service@acme-prod.iam.gserviceaccount.com
      automountServiceAccountToken: true

  - type: terraform_show
    content: |
      {
        "values": {
          "root_module": {
            "resources": [
              {
                "type": "google_sql_database_instance",
                "name": "prod-acme-payments-order-service-cloudsql",
                "values": {
                  "database_version": "POSTGRES_16",
                  "deletion_protection": false,
                  "settings": {
                    "backup_configuration": {
                      "enabled": false
                    },
                    "ip_configuration": {
                      "ipv4_enabled": true,
                      "authorized_networks": [
                        { "value": "0.0.0.0/0" }
                      ]
                    }
                  }
                }
              }
            ]
          }
        }
      }
```

---

## Violations in This Evidence

The following violations are intentionally present for demonstration:

**FAIL — Security:**
- `SEC-001/002`: No `securityContext` block — `runAsNonRoot` and `runAsUser` not set
- `SEC-003`: `allowPrivilegeEscalation` defaults to `true` (not explicitly set to `false`)
- `SEC-004`: `readOnlyRootFilesystem` not set
- `SEC-005`: `capabilities.drop` not configured
- `SEC-009`: `automountServiceAccountToken: true` on ServiceAccount
- `SEC-010`: Image tag is `latest` in production
- `SEC-014`: `DB_PASSWORD` set as a literal string in env (not a `secretKeyRef`)

**FAIL — Network:**
- `NET-001/002/003`: No NetworkPolicy in namespace

**FAIL — Resilience:**
- `RES-001/002`: No PodDisruptionBudget (Tier 1 prod requires `minAvailable: 2`)

**FAIL — DR:**
- `DR-001`: Cloud SQL automated backups disabled
- `DR-005`: `deletion_protection: false` on prod database

**FAIL — Network (infra):**
- `NET-005`: Cloud SQL has `ipv4_enabled: true` with `0.0.0.0/0` — public database endpoint

**PASS:**
- `RES-003/004`: HPA present with `minReplicas: 3`
- `RES-005/006`: Resource requests and limits set
- `OBS-001/002`: Liveness and readiness probes configured
- `OBS-003/004/005`: Prometheus annotations present

**UNKNOWN:**
- `DR-003/004/006`: No evidence of cross-region replica or lag alert (need `gcloud sql instances list`)

**Expected Verdict:** NON-COMPLIANT
