# Sample Application Architecture

Reference architecture for a cloud-native e-commerce platform demonstrating the standards in practice.

---

## System Overview

A full-stack e-commerce demonstration featuring microservices (Java 21/Spring Boot) and React frontend with Google OAuth and local authentication. Supports deployment on both local Kind clusters and GCP Cloud Run.

```mermaid
flowchart TB
    subgraph Users["Users"]
        Web["Web Browser"]
        Mobile["Mobile App"]
    end

    subgraph Edge["Edge Layer"]
        CDN["CDN / Cloud CDN"]
        LB["Load Balancer"]
        Gateway["API Gateway"]
    end

    subgraph Frontend["Frontend Layer"]
        StorefrontUI["Storefront UI<br/>(React/TypeScript)"]
        MobileUI["Mobile UI<br/>(React Native)"]
    end

    subgraph Services["Microservices Layer"]
        Auth["Auth Service<br/>(OAuth/JWT)"]
        Catalog["Catalog Service<br/>(Products)"]
        Cart["Cart Service<br/>(Shopping Cart)"]
        Order["Order Service<br/>(Orders)"]
        Payment["Payment Service<br/>(Payments)"]
        Notification["Notification Service<br/>(Email/SMS)"]
    end

    subgraph Data["Data Layer"]
        AuthDB[(Auth DB)]
        CatalogDB[(Catalog DB)]
        CartDB[(Cart DB<br/>Redis)]
        OrderDB[(Order DB)]
        PaymentDB[(Payment DB)]
    end

    subgraph Events["Event Infrastructure"]
        PubSub["GCP Pub/Sub<br/>/ Kafka"]
    end

    subgraph Observability["Observability"]
        OTel["OpenTelemetry<br/>Collector"]
        Prometheus["Prometheus"]
        Grafana["Grafana"]
        Logging["Cloud Logging"]
    end

    Web --> CDN
    Mobile --> LB
    CDN --> LB
    LB --> Gateway
    Gateway --> StorefrontUI
    Gateway --> MobileUI
    Gateway --> Auth
    Gateway --> Catalog
    Gateway --> Cart
    Gateway --> Order
    Gateway --> Payment

    Auth --> AuthDB
    Catalog --> CatalogDB
    Cart --> CartDB
    Order --> OrderDB
    Payment --> PaymentDB

    Order --> PubSub
    Payment --> PubSub
    PubSub --> Notification
    PubSub --> Order

    Services --> OTel
    OTel --> Prometheus
    OTel --> Logging
    Prometheus --> Grafana
```

---

## Project Structure

### Repository Layout

```
├── .github/                     # GitHub Actions workflows
│   └── workflows/
│       ├── ci.yml               # PR validation
│       ├── build.yml            # Build and test
│       ├── security.yml         # Security scans
│       └── deploy.yml           # Deployment
│
├── services/                    # Backend Microservices
│   ├── auth-service/            # Authentication & Authorization
│   │   ├── src/main/java/
│   │   │   ├── domain/          # Core business logic
│   │   │   ├── application/     # Use cases
│   │   │   ├── infrastructure/  # Adapters
│   │   │   └── api/             # REST controllers
│   │   ├── src/test/
│   │   ├── build.gradle
│   │   └── Dockerfile
│   │
│   ├── catalog-service/         # Product catalog
│   ├── cart-service/            # Shopping cart
│   ├── order-service/           # Order management
│   ├── payment-service/         # Payment processing
│   ├── notification-service/    # Notifications
│   │
│   └── libs/                    # Shared libraries
│       ├── jwt-common/          # JWT utilities
│       ├── event-common/        # Event schemas
│       └── observability/       # OTel configuration
│
├── ui/                          # Frontend Applications
│   ├── storefront-ui/           # React + TypeScript (Vite)
│   │   ├── src/
│   │   │   ├── api/             # API clients
│   │   │   ├── components/      # UI components
│   │   │   ├── features/        # Feature modules
│   │   │   ├── hooks/           # Custom hooks
│   │   │   └── pages/           # Route components
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   ├── mobile-ui/               # React Native
│   └── commons/                 # Shared UI libraries
│
├── infra/                       # Infrastructure as Code
│   ├── terraform/               # GCP resources
│   │   ├── modules/
│   │   │   ├── cloudrun/
│   │   │   ├── cloudsql/
│   │   │   ├── pubsub/
│   │   │   └── networking/
│   │   ├── environments/
│   │   │   ├── nonprod/
│   │   │   └── prod/
│   │   └── main.tf
│   │
│   └── k8s/                     # Kubernetes manifests
│       ├── base/                # Base configurations
│       ├── overlays/
│       │   ├── local/           # Kind cluster
│       │   ├── nonprod/
│       │   └── prod/
│       └── kustomization.yaml
│
├── docs/                        # Documentation
│   ├── adr/                     # Architecture Decision Records
│   ├── api/                     # API documentation
│   └── runbooks/                # Operational runbooks
│
└── scripts/                     # Utility scripts
    ├── local-setup.sh
    └── deploy.sh
```

---

## Service Details

### Service Matrix

| Service | Responsibilities | Database | Events Published | Events Consumed |
|---------|-----------------|----------|------------------|-----------------|
| auth-service | OAuth, JWT, User mgmt | PostgreSQL | UserCreated, UserLoggedIn | - |
| catalog-service | Products, Categories, Search | PostgreSQL | ProductUpdated | - |
| cart-service | Shopping cart, Sessions | Redis | CartUpdated | UserLoggedIn |
| order-service | Orders, Order history | PostgreSQL | OrderCreated, OrderShipped | PaymentProcessed |
| payment-service | Payment processing | PostgreSQL | PaymentProcessed, PaymentFailed | OrderCreated |
| notification-service | Email, SMS, Push | - | - | OrderCreated, PaymentProcessed |

---

## Deployment Architecture

### GCP Cloud Run Deployment

```mermaid
flowchart TB
    subgraph GCP["Google Cloud Platform"]
        subgraph Network["VPC Network"]
            subgraph Public["Public Subnet"]
                GLB["Global Load Balancer"]
                APIGW["Api Gateway"]
                CloudCDN["Cloud CDN"]
            end

            subgraph Private["Private Subnet"]
                subgraph CloudRun["Cloud Run Services"]
                    AuthCR["auth-service"]
                    CatalogCR["catalog-service"]
                    CartCR["cart-service"]
                    OrderCR["order-service"]
                    PaymentCR["payment-service"]
                    NotifCR["notification-service"]
                    FrontendCR["storefront-ui"]
                end

                subgraph Data["Data Services"]
                    CloudSQL["Cloud SQL<br/>(PostgreSQL)"]
                    Memorystore["Memorystore<br/>(Redis)"]
                    PubSub["Cloud Pub/Sub"]
                end
            end
        end

        subgraph GCPServices["GCP Shared Services"]
            CloudMonitor["Cloud Monitoring"]
            CloudTrace["Cloud Trace"]
            CloudLog["Cloud Logging"]
            SecretMgr["Secret Management"]
        end
    end

    Internet["Internet"] --> GLB
    GLB --> CloudCDN
    GLB --> APIGW
    CloudCDN --> FrontendCR
    APIGW --> AuthCR
    APIGW --> CatalogCR
    APIGW --> CartCR
    APIGW --> OrderCR

    CloudRun --> CloudSQL
    CloudRun --> Memorystore
    CloudRun --> PubSub
    CloudRun --> GCPServices
```

---

## Data Flow

### Order Processing Flow

```mermaid
flowchart LR
    subgraph User
        Browser["Browser"]
    end

    subgraph Sync["Synchronous Flow"]
        API["API Gateway"]
        Order["Order Service"]
        Cart["Cart Service"]
        Payment["Payment Service"]
    end

    subgraph Async["Asynchronous Flow"]
        EventBus["Event Bus"]
        Notification["Notification Service"]
        Analytics["Analytics"]
    end

    subgraph Storage
        OrderDB[(Order DB)]
        CartDB[(Cart DB)]
    end

    Browser -->|1. Checkout| API
    API -->|2. Create Order| Order
    Order -->|3. Get Cart| Cart
    Cart -->|4. Cart Items| Order
    Cart -->|8. Clear Cart| CartDB
    Order -->|5. Process Payment| Payment
    Payment -->|6. Payment Result| Order
    Order -->|7. Save Order| OrderDB
    Order -->|9. Publish Event| EventBus
    Order -->|10. Confirmation| Browser

    EventBus -->|11. OrderCreated| Notification
    EventBus -->|12. OrderCreated| Analytics
    Notification -->|13. Email| Browser
```

---

## Event Schema

### Domain Events

```mermaid
classDiagram
    class DomainEvent {
        <<interface>>
        +UUID eventId
        +String eventType
        +Instant occurredAt
        +String aggregateId
    }

    class OrderCreated {
        +UUID orderId
        +UUID customerId
        +Money totalAmount
        +List~OrderLine~ items
    }

    class OrderShipped {
        +UUID orderId
        +String trackingNumber
        +Instant shippedAt
    }

    class PaymentProcessed {
        +UUID paymentId
        +UUID orderId
        +Money amount
        +PaymentStatus status
    }

    class UserCreated {
        +UUID userId
        +String email
        +Instant createdAt
    }

    DomainEvent <|-- OrderCreated
    DomainEvent <|-- OrderShipped
    DomainEvent <|-- PaymentProcessed
    DomainEvent <|-- UserCreated
```

---

## API Structure

### RESTful Endpoints

```
Auth Service
├── POST   /api/v1/auth/login
├── POST   /api/v1/auth/register
├── POST   /api/v1/auth/refresh
├── GET    /api/v1/auth/oauth/google
└── GET    /api/v1/users/me

Catalog Service
├── GET    /api/v1/products
├── GET    /api/v1/products/{id}
├── GET    /api/v1/products/search?q=
├── GET    /api/v1/categories
└── GET    /api/v1/categories/{id}/products

Cart Service
├── GET    /api/v1/cart
├── POST   /api/v1/cart/items
├── PUT    /api/v1/cart/items/{id}
├── DELETE /api/v1/cart/items/{id}
└── DELETE /api/v1/cart

Order Service
├── POST   /api/v1/orders
├── GET    /api/v1/orders
├── GET    /api/v1/orders/{id}
└── POST   /api/v1/orders/{id}/cancel

Payment Service
├── POST   /api/v1/payments
├── GET    /api/v1/payments/{id}
└── POST   /api/v1/payments/{id}/refund
```

---

## Security Architecture

```mermaid
flowchart TB
    subgraph External["External"]
        User["User"]
        IdP["Google IdP"]
    end

    subgraph Edge["Edge Security"]
        WAF["WAF / Cloud Armor"]
        Gateway["API Gateway"]
    end

    subgraph Auth["Authentication"]
        AuthSvc["Auth Service"]
        JWT["JWT Tokens"]
    end

    subgraph Services["Service Mesh"]
        subgraph mTLS["mTLS Encrypted"]
            Svc1["Service A"]
            Svc2["Service B"]
            Svc3["Service C"]
        end
    end

    subgraph Secrets["Secrets Management"]
        SecretMgr["Secret Manager"]
        Rotation["Auto Rotation"]
    end

    User -->|HTTPS| WAF
    WAF --> Gateway
    Gateway -->|OAuth| IdP
    Gateway -->|Validate JWT| AuthSvc
    AuthSvc -->|Issue| JWT
    Gateway -->|mTLS| Services
    Services <-->|mTLS| Services
    Services --> SecretMgr
    SecretMgr --> Rotation
```

---

## Observability Stack

```mermaid
flowchart LR
    subgraph Applications["Applications"]
        App1["Service A"]
        App2["Service B"]
        App3["Service C"]
    end

    subgraph Collection["Collection"]
        OTel["OTel Collector"]
    end

    subgraph Storage["Storage"]
        Prometheus["Prometheus<br/>(Metrics)"]
        Loki["Loki<br/>(Logs)"]
        Tempo["Tempo<br/>(Traces)"]
    end

    subgraph Visualization["Visualization"]
        Grafana["Grafana"]
    end

    subgraph Alerting["Alerting"]
        AlertMgr["Alert Manager"]
        PagerDuty["PagerDuty"]
        Slack["Slack"]
    end

    Applications -->|OTLP| OTel
    OTel --> Prometheus
    OTel --> Loki
    OTel --> Tempo
    Prometheus --> Grafana
    Loki --> Grafana
    Tempo --> Grafana
    Prometheus --> AlertMgr
    AlertMgr --> PagerDuty
    AlertMgr --> Slack
```

---

## Development Workflow

```mermaid
gitGraph
    commit id: "main"
    branch feature/add-payment
    checkout feature/add-payment
    commit id: "feat: add payment endpoint"
    commit id: "test: add payment tests"
    checkout main
    merge feature/add-payment id: "PR #123"
    commit id: "CI: build & test"
    commit id: "Deploy: nonprod"
    commit id: "Deploy: prod (canary)"
    commit id: "Deploy: prod (100%)"
```

---

## Getting Started

### Prerequisites
```bash
# Required tools
java --version    # Java 21+
node --version    # Node.js LTS
docker --version  # Docker
kubectl version   # kubectl
kind version      # Kind (optional)
```

### Local Development
```bash
# Clone repository
git clone https://github.com/org/ecommerce-platform.git
cd ecommerce-platform

# Start infrastructure
docker-compose up -d

# Start backend service
cd services/catalog-service
./gradlew bootRun

# Start frontend
cd ui/storefront-ui
npm install && npm run dev
```

### Local Kubernetes
```bash
# Create Kind cluster
kind create cluster --config infra/k8s/kind-config.yaml

# Deploy all services
kubectl apply -k infra/k8s/overlays/local/

# Port forward
kubectl port-forward svc/storefront-ui 3000:80
```

---

## Related Standards

- [PRINCIPLES.md](./PRINCIPLES.md) - Core engineering principles
- [PATTERNS.md](./PATTERNS.md) - DDD, Hexagonal, Event driven & Resilience patterns
- [TECHNOLOGY-STANDARDS.md](./TECHNOLOGY-STANDARDS.md) - Java/Spring, React standards
- [SECURITY-STANDARDS.md](./SECURITY-STANDARDS.md) - Security implementation
- [DEVOPS-STANDARDS.md](./DEVOPS-STANDARDS.md) - CI/CD pipelines
- [OBSERVABILITY-STANDARDS.md](./OBSERVABILITY-STANDARDS.md) - Monitoring setup
