# Example Input: Audit the payments-prod Namespace

## Request

Audit the `payments-prod` Kubernetes namespace for compliance with the organisation's infrastructure standards.

```
input_type: k8s-namespace
namespace_or_group: payments-prod
environment: prod
cloud_target: k8s
```

## Namespace State (kubectl output)

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payments-api
  namespace: payments-prod
  labels:
    app: payments-api
    Environment: prod
    Application: payments-api
    # Team and CostCentre labels deliberately omitted
spec:
  replicas: 1
  selector:
    matchLabels:
      app: payments-api
  template:
    metadata:
      labels:
        app: payments-api
    spec:
      # No pod-level securityContext
      containers:
        - name: payments-api
          image: us-central1-docker.pkg.dev/acme-project/apps/payments-api:latest
          ports:
            - containerPort: 8080
          # No resources block
          # No readinessProbe
          # No livenessProbe
          securityContext:
            allowPrivilegeEscalation: true
            # runAsNonRoot not set
            # readOnlyRootFilesystem not set
        - name: cloudsql-proxy
          image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.8.0
          # No resources block on sidecar
---
apiVersion: v1
kind: Service
metadata:
  name: payments-api
  namespace: payments-prod
  labels:
    app: payments-api
spec:
  selector:
    app: payments-api
  ports:
    - port: 80
      targetPort: 8080
---
# No HorizontalPodAutoscaler defined
# No NetworkPolicy defined
```

---

## What the Validator Should Find

For illustration — the agent must discover these independently:

| Check ID | Expected Status | Reason |
|----------|----------------|--------|
| CS-01 | FAIL (CRITICAL) | No `runAsNonRoot: true` in pod spec |
| CS-02 | FAIL (CRITICAL) | `allowPrivilegeEscalation: true` explicitly set |
| CS-03 | FAIL (HIGH) | `readOnlyRootFilesystem` not set |
| CS-04 | FAIL (HIGH) | `capabilities.drop: [ALL]` not set |
| CS-05 | UNKNOWN | `runAsUser` not specified — ambiguous |
| RG-01 through RG-04 | FAIL (HIGH) | No `resources` block on either container |
| RG-05 | FAIL (MEDIUM) | No HPA defined |
| RG-06 | FAIL (HIGH) | `replicas: 1` in prod environment (< 2) |
| HP-01 | FAIL (HIGH) | No `readinessProbe` |
| HP-02 | FAIL (HIGH) | No `livenessProbe` |
| IP-01 | FAIL (HIGH) | Image tag is `latest` |
| IP-02 | PASS | Image from approved GCR registry |
| NP-01 through NP-03 | FAIL | No NetworkPolicy in namespace |
| TG-01 | PASS | `Environment: prod` label present |
| TG-02 | PASS | `Application: payments-api` label present |
| TG-03 | FAIL (MEDIUM) | `Team` label missing |
| TG-04 | FAIL (MEDIUM) | `ManagedBy` label missing |
| TG-05 | FAIL (MEDIUM) | `CostCentre` label missing |

## Expected Remediation Plan

### Immediate (CRITICAL)
- Add `securityContext.runAsNonRoot: true` to pod spec.
- Set `allowPrivilegeEscalation: false` on both containers.

### Before Next Release (HIGH)
- Add `resources.requests` and `resources.limits` to `payments-api` and `cloudsql-proxy` containers.
- Replace `latest` image tag with the current Git SHA (`${{ github.sha }}`).
- Add `readinessProbe` and `livenessProbe` to `payments-api`.
- Scale to `replicas: 2` minimum for prod.
- Create a `NetworkPolicy` with default-deny ingress and egress.

### Planned (MEDIUM)
- Add `Team`, `ManagedBy`, and `CostCentre` labels.
- Create HorizontalPodAutoscaler (min: 2, max: 10, target CPU: 70%).
- Set `seccompProfile.type: RuntimeDefault`.
