# DevOps Standards

Tools and standards for CI/CD, deployment, and developer experience.

---

## Tools

| Tools | Capabilities | Details |
|---------|----------|----------|
| GitHub  | Source Control, Secrets   | All code to be maintained in GitHub   |
| GitHub Actions  | Build and Deploy pipelines   | All build and deployment via GitHub Actions   |
| Code quality and security  | Sonar Scanner  | Static Code Aanalysis   |
| Build scripting| Gradle, npm | Gradle for all java build scripting, npm for front-end node |
| Secret Management  | GitHub Secrets & GCP   | Secrets for build and deploy in GitHub and GCP for runtime secrets   |
| Infrastructure as Code | Terraform | All infrastructure provisioning to be done via Terraform  |
| IDE | VS Code   | Engineers to use VSCode as IDE  |
| Artifact management | GCP Artifact Registry   | All generated artifadcts  |
| Unit testing | Junit (Java), Jest(JS)   | Junit for java tests, Jest for javascript  |
| Contract testing | PACT   | contract-based testing for Consumer-Driven tests |
| Integration testing | Cucumber, Testcontainers  | BDD Style tests for integration tests  and test containers to manage services|
| Performance testing | Grafana K6    |  Use K6 for load and performance testing of critical flows  |


## Branching Strategy

### Trunk-Based Development
- `main` is the single source of truth
- `main` is always deployable
- `main` is protected and requires PR approvals
- Short-lived feature branches (< 2 days)
- No long-running release branches

### Branch Naming
```
feature/TICKET-123-add-order-api
fix/TICKET-456-null-pointer-exception
chore/update-dependencies
docs/api-documentation
```

### Commit Messages
Follow Conventional Commits:
```
feat: add order creation endpoint
fix: handle null customer ID gracefully
refactor: extract order validation logic
docs: update API documentation
chore: update Spring Boot to 3.4.0
test: add integration tests for payment flow
```

---

## CI/CD Pipeline

### Pipeline Stages
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Build    │ -> │    Test     │ -> │   Security  │ -> │   Deploy    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     │                   │                   │                   │
     ├── Compile         ├── Unit            ├── SAST            ├── Non-Prod
     ├── Dependencies    ├── Integration     ├── SCA             ├── Prod
     └── Artifact Build  ├── Contract        ├── DAST            └── Release (BG/Canary)
                         └── Performance     └── Container Scan
```

### GitHub Actions Structure
```
.github/
├── workflows/
│   ├── ci.yml              # PR validation
│   ├── build.yml           # Build and test
│   ├── security.yml        # Security scans
│   ├── deploy-nonprod.yml  # Non-prod deployment
│   └── deploy-prod.yml     # Production deployment
└── actions/
    ├── setup-java/         # Reusable setup
    └── deploy-cloudrun/    # Reusable deploy
```

### CI Workflow Example
```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 21
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '21'
          cache: 'gradle'

      - name: Build
        run: ./gradlew clean build -x test

      - name: Unit Tests
        run: ./gradlew test

      - name: Integration Tests
        run: ./gradlew integrationTest

      - name: Code Coverage
        run: ./gradlew jacocoTestReport

      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./build/reports/jacoco/test/jacocoTestReport.xml

  security:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4

      - name: OWASP Dependency Check
        run: ./gradlew dependencyCheckAnalyze

      - name: SonarQube Scan
        run: ./gradlew sonar
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

---

## Deployment Strategies

### Environment Progression
```
Feature Branch -> Non-Production -> Production
       │               │                │
       └── PR Tests    └── Full Tests   └── Blue Green/Canary + Full
```

### Canary Deployment
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: order-service
spec:
  replicas: 5
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: {duration: 5m}
        - setWeight: 25
        - pause: {duration: 5m}
        - setWeight: 50
        - pause: {duration: 5m}
        - setWeight: 100
      analysis:
        templates:
          - templateName: success-rate
        startingStep: 1
```

### Blue-Green Deployment
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: order-service
spec:
  replicas: 3
  strategy:
    blueGreen:
      activeService: order-service-active
      previewService: order-service-preview
      autoPromotionEnabled: false
```

### Rollback Triggers
- Error rate > 5% for 2 minutes
- Latency p99 > 2x baseline
- Circuit breaker open
- Health check failures

---

## GitOps

### ArgoCD Application
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: order-service
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/config-repo
    targetRevision: main
    path: environments/production/order-service
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### Repository Structure
```
config-repo/
├── base/
│   └── order-service/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── kustomization.yaml
└── environments/
    ├── nonprod/
    │   └── order-service/
    │       ├── kustomization.yaml
    │       └── patches/
    └── production/
        └── order-service/
            ├── kustomization.yaml
            └── patches/
```

---

## Testing Strategy

### Test Pyramid
```
         /\
        /  \        E2E Tests (Few)
       /────\       - Critical paths only
      /      \      - Run pre-deploy
     /────────\     Integration Tests (Some)
    /          \    - Service boundaries
   /────────────\   - Testcontainers
  /              \  Unit Tests (Many)
 /────────────────\ - Fast, isolated
```

### Testing Requirements
| Type | Coverage | When Run |
|------|----------|----------|
| Unit | > 80% | Every commit |
| Integration | Critical paths | Every PR |
| Contract | API boundaries | Every PR |
| E2E | Happy paths | Pre-deploy |
| Performance | Baseline | Weekly + pre-release |

### Contract Testing (Pact)
```java
@Pact(consumer = "order-service", provider = "catalog-service")
public RequestResponsePact getProductPact(PactDslWithProvider builder) {
    return builder
        .given("product exists")
        .uponReceiving("get product by id")
        .path("/api/v1/products/123")
        .method("GET")
        .willRespondWith()
        .status(200)
        .body(newJsonBody(body -> {
            body.stringType("id", "123");
            body.stringType("name", "Product Name");
            body.decimalType("price", 99.99);
        }).build())
        .toPact();
}
```

---

## Release Management

### Versioning
- Semantic versioning: `MAJOR.MINOR.PATCH`
- Container images tagged with git SHA + version
- Immutable releases - never overwrite tags

### Release Notes
Automated from conventional commits:
```yaml
- name: Generate Release Notes
  uses: release-drafter/release-drafter@v5
  with:
    config-name: release-drafter.yml
```

### Release Process
1. Merge to main triggers build
2. Automated tests and security scans
3. Build versioned, immutable artifact
4. Deploy to non-production
5. Run E2E tests
6. Manual approval for production
7. Progressive rollout to production
8. Automated rollback if metrics degrade

---

## Developer Experience

### Local Development
```yaml
# docker-compose.yml for local dependencies
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: orderdb
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Local Kubernetes (Kind)
```yaml
# kind-config.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
```

### Skaffold Configuration
```yaml
apiVersion: skaffold/v4beta6
kind: Config
metadata:
  name: order-service
build:
  artifacts:
    - image: order-service
      docker:
        dockerfile: Dockerfile
deploy:
  kubectl:
    manifests:
      - k8s/*.yaml
```

### Inner Loop Optimization
- Hot reload for local development
- Fast incremental builds
- Local container registry
- Port forwarding for debugging

---

## Environment Management

### Environment Parity
All environments should be as similar as possible:
- Same container images
- Same Kubernetes configurations (with env-specific patches)
- Same network policies
- Different only: secrets, scaling, resource limits

### Environment Variables
```yaml
# base configuration
spec:
  containers:
    - name: order-service
      env:
        - name: SPRING_PROFILES_ACTIVE
          value: "kubernetes"
        - name: DB_HOST
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: host
```

### Feature Flags
- Use external feature flag service (LaunchDarkly, Unleash)
- Default to feature off in production
- Gradual rollout percentage
- Kill switch for emergencies
