# Technology Standards

Technology stack and standards for selection and implementation.

---

### Technology Stack
- **API Gateway**: Native API Gateway for rate limiting at the edge, request routing, or API composition patterns
- **Backend**: Latest Java LTS (25+), Spring Boot 4.0+, Gradle (multi-module monorepo)
- **Frontend**: React with TypeScript, Vite
- **Spring Cloud**: Microservices patterns and distributed system support
- **Containers**: Docker for all services
- **Orchestration**: Kubernetes (Kind locally, Cloud Run on GCP)
- **Infrastructure**: Terraform for IaC to setup core GCP resources
- **Database**: CloudSQL (GCP), local SQL/H2 for development
- **Caching**: Redis, cloud native
- **Secrets**: GCP Secrets manager for runtime, GitHub secrets for build
- **Events/Integration**: GCP Pub/Sub, Kafka
- **Config**: YAML for all Kubernetes and application configs
- **OpenTelemetry**: Unified observability (traces, metrics, logs)
- **React 19+**: Latest react library for web and native use interfaces.

---

## Backend: Java/Spring

### Version Requirements
- **Java**: Latest LTS (21+), prefer 25 when available
- **Spring Boot**: 3.4+ (4.0+ when stable)
- **Spring Framework**: 6.x (7.x with Spring Boot 4)
- **Gradle**: Latest stable for build automation

### Java Standards
```java
// Use records for immutable data
public record OrderId(UUID value) {
    public OrderId {
        Objects.requireNonNull(value, "OrderId cannot be null");
    }
}

// Use sealed classes for type safety
public sealed interface PaymentMethod
    permits CreditCard, DebitCard, BankTransfer {}

// Use pattern matching
public String describe(PaymentMethod method) {
    return switch (method) {
        case CreditCard cc -> "Credit: " + cc.lastFour();
        case DebitCard dc -> "Debit: " + dc.lastFour();
        case BankTransfer bt -> "Bank: " + bt.accountMask();
    };
}

// Use virtual threads for I/O-bound operations
@Bean
public Executor taskExecutor() {
    return Executors.newVirtualThreadPerTaskExecutor();
}
```

### Spring Boot Configuration
```java
@SpringBootApplication
@EnableCaching
@EnableAsync
@EnableScheduling
public class ServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(ServiceApplication.class, args);
    }
}

// Constructor injection (no @Autowired on constructors)
@Service
public class OrderService {
    private final OrderRepository orderRepository;
    private final EventPublisher eventPublisher;

    public OrderService(OrderRepository orderRepository,
                       EventPublisher eventPublisher) {
        this.orderRepository = orderRepository;
        this.eventPublisher = eventPublisher;
    }
}
```

### Application Configuration
```yaml
# application.yml
spring:
  application:
    name: order-service
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:local}

server:
  port: 8080
  shutdown: graceful

management:
  endpoints:
    web:
      exposure:
        include: health,metrics,prometheus,info
  endpoint:
    health:
      show-details: when_authorized
      probes:
        enabled: true
```

### Build Configuration (Gradle)
```gradle
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.4.0'
    id 'io.spring.dependency-management' version '1.1.4'
    id 'jacoco'
}

java {
    sourceCompatibility = '21'
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
    implementation 'org.springframework.boot:spring-boot-starter-validation'

    runtimeOnly 'org.postgresql:postgresql'
    runtimeOnly 'io.micrometer:micrometer-registry-prometheus'

    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation 'org.testcontainers:postgresql'
}

test {
    useJUnitPlatform()
    finalizedBy jacocoTestReport
}
```

---

## Frontend: React/TypeScript

### Version Requirements
- **React**: 19+
- **TypeScript**: 5.x with strict mode
- **Vite**: Latest stable for build tooling
- **Node.js**: LTS version

### TypeScript Configuration
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

### React Standards
```typescript
// Use functional components with hooks
interface OrderProps {
  orderId: string;
  onUpdate: (order: Order) => void;
}

export const OrderDetails: React.FC<OrderProps> = ({ orderId, onUpdate }) => {
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOrder(orderId)
      .then(setOrder)
      .finally(() => setLoading(false));
  }, [orderId]);

  if (loading) return <Spinner />;
  if (!order) return <NotFound />;

  return <OrderView order={order} onUpdate={onUpdate} />;
};

// API clients in src/api/
export const orderApi = {
  getOrder: (id: string): Promise<Order> =>
    fetch(`/api/v1/orders/${id}`).then(handleResponse),

  createOrder: (data: CreateOrderRequest): Promise<Order> =>
    fetch('/api/v1/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
};
```

### Project Structure
```
src/
├── api/              # API clients
├── components/       # Reusable UI components
├── features/         # Feature-specific components
├── hooks/            # Custom React hooks
├── pages/            # Route components
├── store/            # State management
├── types/            # TypeScript interfaces
└── utils/            # Helper functions
```

---

## Database

### PostgreSQL Standards
- Use CloudSQL (GCP) for production
- H2 or local PostgreSQL for development
- Connection pooling via HikariCP
- Flyway for migrations

### Migration Standards
```sql
-- V1__create_orders_table.sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,
    total_amount DECIMAL(19,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
```

### Naming Conventions
- Tables: lowercase, plural (`orders`, `order_lines`)
- Columns: lowercase, snake_case (`customer_id`, `created_at`)
- Indexes: `idx_<table>_<column>`
- Foreign keys: `fk_<table>_<referenced_table>`

---

## Caching

### Redis Standards
- Use managed Redis (e.g., GCP Memorystore)
- Connection pooling via Lettuce
- TTL on all cache entries
- Cache key namespacing

### Configuration
```java
@Configuration
@EnableCaching
public class CacheConfig {
    @Bean
    public CacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration config = RedisCacheConfiguration
            .defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10))
            .serializeKeysWith(SerializationPair
                .fromSerializer(new StringRedisSerializer()))
            .serializeValuesWith(SerializationPair
                .fromSerializer(new GenericJackson2JsonRedisSerializer()));

        return RedisCacheManager.builder(factory)
            .cacheDefaults(config)
            .withCacheConfiguration("orders",
                config.entryTtl(Duration.ofMinutes(5)))
            .build();
    }
}
```

### Cache Patterns
| Pattern | Use Case |
|---------|----------|
| Cache-Aside | Read-heavy, tolerate stale data |
| Write-Through | Consistency critical |
| Write-Behind | High write volume |

---

## Containers

### Docker Standards
```dockerfile
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app
COPY . .
RUN ./gradlew clean bootJar --no-daemon

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

# Run as non-root
RUN addgroup -g 1001 appuser && \
    adduser -D -u 1001 -G appuser appuser
USER appuser

COPY --from=builder /app/build/libs/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", \
    "-XX:+UseZGC", \
    "-XX:+UseContainerSupport", \
    "-XX:MaxRAMPercentage=75.0", \
    "-jar", "app.jar"]
```

### Image Requirements
- Multi-stage builds for minimal size
- Non-root user execution
- No secrets in images
- Versioned tags (no `latest` in production)
- Base images from trusted sources

---

## Messaging

### Kafka/Pub-Sub Standards
- Schema registry for all events
- Avro or Protobuf serialization
- Dead-letter queue for failed messages
- Idempotent consumers

### Event Schema Example (Avro)
```avro
{
  "type": "record",
  "name": "OrderCreatedEvent",
  "namespace": "com.example.events",
  "fields": [
    {"name": "eventId", "type": "string"},
    {"name": "orderId", "type": "string"},
    {"name": "customerId", "type": "string"},
    {"name": "totalAmount", "type": "double"},
    {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"}
  ]
}
```

---

## Tool Matrix

| Category | Tool | Purpose |
|----------|------|---------|
| IDE | VS Code | Primary development environment |
| Source Control | GitHub | Code repository and collaboration |
| CI/CD | GitHub Actions | Build and deployment pipelines |
| Build (Java) | Gradle | Java project build automation |
| Build (JS) | npm/Vite | Frontend build tooling |
| Code Quality | SonarQube | Static code analysis |
| Security Scan | OWASP Dependency Check | Vulnerability scanning |
| Unit Test (Java) | JUnit 5 | Java unit testing |
| Unit Test (JS) | Jest | JavaScript testing |
| Contract Test | Pact | Consumer-driven contracts |
| Integration Test | Testcontainers, Cucumber | End-to-end testing |
| Performance Test | Grafana K6 | Load and performance testing |
| Infrastructure | Terraform | Infrastructure as Code |
| Container Registry | GCP Artifact Registry | Docker image storage |
