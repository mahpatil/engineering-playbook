# Domain-Driven Cloud Native Microservice

## Overview
This document outlines the architecture and implementation guidelines for building a production-ready, domain-driven cloud native microservice using modern Java technologies and best practices.

## Technology Stack

### Core Technologies
- **Java 25**: Latest LTS features including virtual threads, pattern matching, and structured concurrency
- **Spring Boot 4.0+**: Application framework with Spring Framework 7
- **Spring Cloud**: Microservices patterns and distributed system support
- **OpenTelemetry**: Unified observability (traces, metrics, logs)

### Architecture Patterns
- **Domain-Driven Design (DDD)**: Strategic and tactical patterns
- **Hexagonal Architecture**: Ports and adapters for clean separation
- **Event-Driven Architecture**: Asynchronous communication where appropriate
- **CQRS**: Command Query Responsibility Segregation for complex domains

## Project Structure

```
src/main/java/
├── domain/             # Core business logic (no framework dependencies)
│   ├── model/          # Entities, Value Objects, Aggregates
│   ├── repository/     # Repository interfaces (ports)
│   ├── service/        # Domain services
│   └── event/          # Domain events
├── application/         # Application services and use cases
│   ├── command/        # Command handlers
│   ├── query/          # Query handlers
│   └── dto/            # Data transfer objects
├── infrastructure/      # Technical implementations (adapters)
│   ├── persistence/    # JPA/database implementations
│   ├── messaging/      # Event publishing/consuming
│   ├── cache/          # Caching implementations
│   └── external/       # External service clients
└── api/                # REST/GraphQL controllers
    ├── rest/
    └── graphql/
```

## Core Implementation Guidelines

### 1. Domain-Driven Design Implementation

#### Bounded Contexts
- Clearly define bounded contexts with ubiquitous language
- Each microservice represents one bounded context
- Use context mapping for inter-service relationships

#### Aggregates and Entities
```java
@Entity
public class Order {
    @Id
    private OrderId id;
    private CustomerId customerId;
    private OrderStatus status;

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderLine> orderLines;

    // Enforce invariants
    public void addOrderLine(Product product, int quantity) {
        validateOrderLine(product, quantity);
        orderLines.add(new OrderLine(product, quantity));
        applyEvent(new OrderLineAdded(id, product.getId(), quantity));
    }
}
```

#### Value Objects
```java
public record OrderId(UUID value) {
    public OrderId {
        Objects.requireNonNull(value, "OrderId cannot be null");
    }
}
```

#### Domain Events
```java
public record OrderCreated(
    OrderId orderId,
    CustomerId customerId,
    Instant occurredAt
) implements DomainEvent {}
```

### 2. Spring Framework 7 Configuration

#### Application Configuration
```java
@SpringBootApplication
@EnableCaching
@EnableAsync
@EnableScheduling
public class MicroserviceApplication {
    public static void main(String[] args) {
        SpringApplication.run(MicroserviceApplication.class, args);
    }
}
```

#### Dependency Injection with Hexagonal Architecture
```java
@Configuration
public class ApplicationConfig {

    @Bean
    public OrderService orderService(
        OrderRepository orderRepository,
        EventPublisher eventPublisher,
        DomainValidator validator
    ) {
        return new OrderServiceImpl(orderRepository, eventPublisher, validator);
    }
}
```

### 3. Observability with OpenTelemetry

#### Configuration
```yaml
# application.yml
management:
  otlp:
    metrics:
      export:
        enabled: true
        url: http://otel-collector:4318/v1/metrics
    tracing:
      endpoint: http://otel-collector:4318/v1/traces

  metrics:
    export:
      prometheus:
        enabled: true
    distribution:
      percentiles-histogram:
        http.server.requests: true

  tracing:
    sampling:
      probability: 1.0

  endpoints:
    web:
      exposure:
        include: health,metrics,prometheus,info
```

#### Custom Instrumentation
```java
@Service
public class OrderServiceImpl {

    private final Tracer tracer;
    private final Meter meter;
    private final Counter orderCreatedCounter;

    public OrderServiceImpl(OpenTelemetry openTelemetry) {
        this.tracer = openTelemetry.getTracer("order-service");
        this.meter = openTelemetry.getMeter("order-service");
        this.orderCreatedCounter = meter.counterBuilder("orders.created")
            .setDescription("Number of orders created")
            .build();
    }

    @WithSpan
    public Order createOrder(CreateOrderCommand command) {
        Span span = tracer.spanBuilder("createOrder")
            .setAttribute("customer.id", command.customerId().toString())
            .startSpan();

        try (var scope = span.makeCurrent()) {
            Order order = processOrder(command);
            orderCreatedCounter.add(1);
            return order;
        } catch (Exception e) {
            span.recordException(e);
            throw e;
        } finally {
            span.end();
        }
    }
}
```

#### Structured Logging
```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class OrderProcessor {
    private static final Logger log = LoggerFactory.getLogger(OrderProcessor.class);

    public void process(Order order) {
        log.atInfo()
            .addKeyValue("orderId", order.getId())
            .addKeyValue("customerId", order.getCustomerId())
            .addKeyValue("amount", order.getTotalAmount())
            .log("Processing order");
    }
}
```

### 4. Caching Strategy

#### Multi-Level Caching
```java
@Configuration
@EnableCaching
public class CacheConfig {

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory connectionFactory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10))
            .serializeKeysWith(RedisSerializationContext.SerializationPair
                .fromSerializer(new StringRedisSerializer()))
            .serializeValuesWith(RedisSerializationContext.SerializationPair
                .fromSerializer(new GenericJackson2JsonRedisSerializer()));

        return RedisCacheManager.builder(connectionFactory)
            .cacheDefaults(config)
            .withCacheConfiguration("products",
                config.entryTtl(Duration.ofHours(1)))
            .withCacheConfiguration("orders",
                config.entryTtl(Duration.ofMinutes(5)))
            .build();
    }
}
```

#### Cache Usage
```java
@Service
public class ProductService {

    @Cacheable(value = "products", key = "#id")
    public Product getProduct(ProductId id) {
        return productRepository.findById(id)
            .orElseThrow(() -> new ProductNotFoundException(id));
    }

    @CacheEvict(value = "products", key = "#product.id")
    public void updateProduct(Product product) {
        productRepository.save(product);
    }

    @Caching(evict = {
        @CacheEvict(value = "products", allEntries = true),
        @CacheEvict(value = "productCategories", allEntries = true)
    })
    public void refreshCache() {
        // Bulk operation that invalidates multiple caches
    }
}
```

### 5. High Availability (HA)

#### Database Configuration
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20
      minimum-idle: 10
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000

  jpa:
    properties:
      hibernate:
        connection:
          provider_disables_autocommit: true
        jdbc:
          batch_size: 20
        order_inserts: true
        order_updates: true
```

#### Health Checks
```java
@Component
public class CustomHealthIndicator implements HealthIndicator {

    private final OrderRepository orderRepository;
    private final RedisConnectionFactory redisFactory;

    @Override
    public Health health() {
        try {
            orderRepository.count(); // Database check
            redisFactory.getConnection().ping(); // Cache check

            return Health.up()
                .withDetail("database", "available")
                .withDetail("cache", "available")
                .build();
        } catch (Exception e) {
            return Health.down()
                .withException(e)
                .build();
        }
    }
}
```

#### Graceful Shutdown
```yaml
server:
  shutdown: graceful

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

### 6. Scaling Strategy

#### Horizontal Scaling
- Stateless service design
- Externalized session management (Redis)
- Distributed caching
- Load balancing ready

#### Resource Configuration
```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: order-service
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

#### Auto-scaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: order-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 7. Circuit Breakers and Resilience

#### Resilience4j Configuration
```java
@Configuration
public class ResilienceConfig {

    @Bean
    public CircuitBreakerConfig circuitBreakerConfig() {
        return CircuitBreakerConfig.custom()
            .failureRateThreshold(50)
            .waitDurationInOpenState(Duration.ofSeconds(30))
            .slidingWindowSize(10)
            .minimumNumberOfCalls(5)
            .build();
    }

    @Bean
    public RetryConfig retryConfig() {
        return RetryConfig.custom()
            .maxAttempts(3)
            .waitDuration(Duration.ofMillis(500))
            .retryExceptions(TimeoutException.class, ConnectException.class)
            .build();
    }
}
```

#### Usage Example
```java
@Service
public class ExternalPaymentService {

    private final CircuitBreaker circuitBreaker;
    private final Retry retry;

    @CircuitBreaker(name = "payment-service", fallbackMethod = "paymentFallback")
    @Retry(name = "payment-service")
    @TimeLimiter(name = "payment-service")
    public PaymentResult processPayment(PaymentRequest request) {
        return paymentClient.process(request);
    }

    private PaymentResult paymentFallback(PaymentRequest request, Exception ex) {
        log.warn("Payment service unavailable, queuing for later processing", ex);
        return PaymentResult.queued(request.transactionId());
    }
}
```

#### Bulkhead Pattern
```java
@Configuration
public class BulkheadConfig {

    @Bean
    public ThreadPoolBulkheadConfig threadPoolBulkheadConfig() {
        return ThreadPoolBulkheadConfig.custom()
            .maxThreadPoolSize(10)
            .coreThreadPoolSize(5)
            .queueCapacity(100)
            .build();
    }
}
```

### 8. Automated Testing

#### Unit Tests
```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private EventPublisher eventPublisher;

    @InjectMocks
    private OrderServiceImpl orderService;

    @Test
    void shouldCreateOrderSuccessfully() {
        // Given
        var command = new CreateOrderCommand(
            customerId,
            List.of(new OrderLineDto(productId, 2))
        );

        when(orderRepository.save(any(Order.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));

        // When
        Order order = orderService.createOrder(command);

        // Then
        assertNotNull(order.getId());
        assertEquals(customerId, order.getCustomerId());
        verify(eventPublisher).publish(any(OrderCreated.class));
    }
}
```

#### Integration Tests
```java
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@Testcontainers
@ActiveProfiles("test")
class OrderIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
        .withDatabaseName("testdb");

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine")
        .withExposedPorts(6379);

    @Autowired
    private TestRestTemplate restTemplate;

    @Test
    void shouldCreateAndRetrieveOrder() {
        // Given
        var request = new CreateOrderRequest(customerId, orderLines);

        // When
        var response = restTemplate.postForEntity(
            "/api/v1/orders",
            request,
            OrderResponse.class
        );

        // Then
        assertEquals(HttpStatus.CREATED, response.getStatusCode());
        assertNotNull(response.getBody().orderId());
    }
}
```

#### Contract Tests
```java
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@AutoConfigureRestDocs
class OrderApiContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void shouldDocumentCreateOrder() throws Exception {
        mockMvc.perform(post("/api/v1/orders")
            .contentType(MediaType.APPLICATION_JSON)
            .content(orderJson))
            .andExpect(status().isCreated())
            .andDo(document("create-order",
                requestFields(
                    fieldWithPath("customerId").description("Customer identifier"),
                    fieldWithPath("orderLines").description("List of order lines")
                ),
                responseFields(
                    fieldWithPath("orderId").description("Created order identifier"),
                    fieldWithPath("status").description("Order status")
                )
            ));
    }
}
```

#### Performance Tests
```java
@SpringBootTest
class OrderPerformanceTest {

    @Autowired
    private OrderService orderService;

    @Test
    @Timeout(value = 100, unit = TimeUnit.MILLISECONDS)
    void orderCreationShouldBeFast() {
        orderService.createOrder(createOrderCommand);
    }
}
```

### 9. Deployment

#### Docker Configuration
```dockerfile
# Dockerfile
FROM eclipse-temurin:25-jdk-alpine AS builder
WORKDIR /app
COPY . .
RUN ./gradlew clean bootJar --no-daemon

FROM eclipse-temurin:25-jre-alpine
WORKDIR /app

# Security: Run as non-root user
RUN addgroup -g 1001 appuser && adduser -D -u 1001 -G appuser appuser
USER appuser

COPY --from=builder /app/build/libs/*.jar app.jar

# OpenTelemetry Java agent
ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar /app/opentelemetry-javaagent.jar

EXPOSE 8080
ENTRYPOINT ["java", \
    "-javaagent:/app/opentelemetry-javaagent.jar", \
    "-XX:+UseZGC", \
    "-XX:+UseContainerSupport", \
    "-XX:MaxRAMPercentage=75.0", \
    "-jar", \
    "app.jar"]
```

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  labels:
    app: order-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
    spec:
      containers:
      - name: order-service
        image: order-service:latest
        ports:
        - containerPort: 8080
        env:
        - name: SPRING_PROFILES_ACTIVE
          value: "production"
        - name: OTEL_SERVICE_NAME
          value: "order-service"
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: "http://otel-collector:4318"
        livenessProbe:
          httpGet:
            path: /actuator/health/liveness
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /actuator/health/readiness
            port: 8080
          initialDelaySeconds: 20
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: order-service
spec:
  selector:
    app: order-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
```

#### CI/CD Pipeline (GitHub Actions)
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build-and-test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up JDK 25
      uses: actions/setup-java@v4
      with:
        distribution: 'temurin'
        java-version: '25'
        cache: 'gradle'

    - name: Make gradlew executable
      run: chmod +x ./gradlew

    - name: Build
      run: ./gradlew clean build -x test

    - name: Unit Tests
      run: ./gradlew test

    - name: Integration Tests
      run: ./gradlew integrationTest

    - name: Code Coverage
      run: ./gradlew jacocoTestReport

    - name: Upload Coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./build/reports/jacoco/test/jacocoTestReport.xml

  security-scan:
    runs-on: ubuntu-latest
    needs: build-and-test

    steps:
    - uses: actions/checkout@v4

    - name: Set up JDK 25
      uses: actions/setup-java@v4
      with:
        distribution: 'temurin'
        java-version: '25'
        cache: 'gradle'

    - name: Make gradlew executable
      run: chmod +x ./gradlew

    - name: OWASP Dependency Check
      run: ./gradlew dependencyCheckAnalyze

    - name: Trivy Container Scan
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'

    - name: SonarQube Scan
      run: |
        ./gradlew sonar \
          -Dsonar.host.url=${{ secrets.SONAR_HOST_URL }} \
          -Dsonar.token=${{ secrets.SONAR_TOKEN }}

  deploy:
    runs-on: ubuntu-latest
    needs: [build-and-test, security-scan]
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v4

    - name: Build Docker Image
      run: docker build -t order-service:${{ github.sha }} .

    - name: Push to Registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push order-service:${{ github.sha }}

    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/order-service \
          order-service=order-service:${{ github.sha }}
```

### 10. Security

#### Security Configuration
```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health/**").permitAll()
                .requestMatchers("/api/v1/**").authenticated()
                .anyRequest().denyAll()
            )
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt.jwtAuthenticationConverter(jwtConverter()))
            )
            .csrf(csrf -> csrf
                .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
            )
            .headers(headers -> headers
                .contentSecurityPolicy(csp ->
                    csp.policyDirectives("default-src 'self'"))
                .frameOptions(frameOptions -> frameOptions.deny())
            );

        return http.build();
    }
}
```

#### OWASP Dependency Check
```gradle
// build.gradle
plugins {
    id 'org.owasp.dependencycheck' version '9.0.0'
}

dependencyCheck {
    failBuildOnCVSS = 7
    suppressionFile = 'dependency-check-suppressions.xml'
    analyzers {
        assemblyEnabled = false
    }
}
```

#### Security Tests
```java
@SpringBootTest
@AutoConfigureMockMvc
class SecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void shouldRejectUnauthenticatedRequests() throws Exception {
        mockMvc.perform(get("/api/v1/orders"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(roles = "USER")
    void shouldAllowAuthenticatedRequests() throws Exception {
        mockMvc.perform(get("/api/v1/orders"))
            .andExpect(status().isOk());
    }

    @Test
    void shouldEnforceRateLimiting() throws Exception {
        for (int i = 0; i < 100; i++) {
            mockMvc.perform(get("/api/v1/orders"));
        }

        mockMvc.perform(get("/api/v1/orders"))
            .andExpect(status().isTooManyRequests());
    }
}
```

## Observability Dashboard

### Metrics to Monitor
1. **Application Metrics**
   - Request rate, latency percentiles (p50, p95, p99)
   - Error rate by endpoint
   - JVM metrics (heap, GC, threads)
   - Database connection pool usage

2. **Business Metrics**
   - Orders created per minute
   - Order processing duration
   - Cache hit/miss ratio
   - Circuit breaker state changes

3. **Infrastructure Metrics**
   - CPU and memory utilization
   - Network I/O
   - Disk usage
   - Pod restart count

### Alerting Rules
```yaml
# alerts.yml
groups:
- name: order-service
  interval: 30s
  rules:
  - alert: HighErrorRate
    expr: rate(http_server_requests_seconds_count{status=~"5.."}[5m]) > 0.05
    for: 2m
    annotations:
      summary: "High error rate detected"

  - alert: CircuitBreakerOpen
    expr: resilience4j_circuitbreaker_state{state="open"} > 0
    for: 1m
    annotations:
      summary: "Circuit breaker is open"
```

## Performance Optimization

### JVM Tuning
```bash
JAVA_OPTS="-XX:+UseZGC \
  -XX:+UseContainerSupport \
  -XX:MaxRAMPercentage=75.0 \
  -XX:+AlwaysPreTouch \
  -XX:+DisableExplicitGC \
  -XX:+ParallelRefProcEnabled \
  -Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags"
```

### Database Optimization
- Connection pooling (HikariCP)
- Query optimization with indexes
- Read replicas for scaling reads
- Database-level caching

### Virtual Threads (Java 21+)
```java
@Configuration
public class AsyncConfig {

    @Bean
    public Executor taskExecutor() {
        return Executors.newVirtualThreadPerTaskExecutor();
    }
}
```

## Best Practices Checklist

- [ ] Domain model free of framework dependencies
- [ ] Clear bounded contexts defined
- [ ] Comprehensive test coverage (>80%)
- [ ] All external calls protected with circuit breakers
- [ ] Distributed tracing implemented
- [ ] Structured logging with correlation IDs
- [ ] Health checks configured
- [ ] Graceful shutdown implemented
- [ ] Security scans in CI/CD
- [ ] Auto-scaling configured
- [ ] Monitoring and alerting set up
- [ ] Database migrations automated (Flyway/Liquibase)
- [ ] API versioning strategy defined
- [ ] Rate limiting implemented
- [ ] Documentation up to date

## Additional Resources


### Dependencies (build.gradle)
```gradle
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.4.0'
    id 'io.spring.dependency-management' version '1.1.4'
    id 'jacoco'
    id 'org.owasp.dependencycheck' version '9.0.0'
    id 'org.sonarqube' version '4.4.1.3373'
}

group = 'com.example'
version = '0.0.1-SNAPSHOT'

java {
    sourceCompatibility = '25'
}

configurations {
    compileOnly {
        extendsFrom annotationProcessor
    }
}

repositories {
    mavenCentral()
}

ext {
    set('testcontainersVersion', "1.19.3")
    set('resilience4jVersion', "2.2.0")
    set('opentelemetryVersion', "1.34.1")
}

dependencies {
    // Spring Boot
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-cache'
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
    implementation 'org.springframework.boot:spring-boot-starter-security'
    implementation 'org.springframework.boot:spring-boot-starter-oauth2-resource-server'
    implementation 'org.springframework.boot:spring-boot-starter-validation'

    // OpenTelemetry
    implementation platform("io.opentelemetry:opentelemetry-bom:${opentelemetryVersion}")
    implementation 'io.opentelemetry:opentelemetry-api'
    implementation 'io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter'

    // Resilience4j
    implementation platform("io.github.resilience4j:resilience4j-bom:${resilience4jVersion}")
    implementation 'io.github.resilience4j:resilience4j-spring-boot3'
    implementation 'io.github.resilience4j:resilience4j-circuitbreaker'
    implementation 'io.github.resilience4j:resilience4j-retry'
    implementation 'io.github.resilience4j:resilience4j-bulkhead'
    implementation 'io.github.resilience4j:resilience4j-timelimiter'

    // Caching
    implementation 'org.springframework.boot:spring-boot-starter-data-redis'
    implementation 'io.lettuce:lettuce-core'

    // Database
    runtimeOnly 'org.postgresql:postgresql'
    implementation 'org.flywaydb:flyway-core'
    implementation 'org.flywaydb:flyway-database-postgresql'

    // Observability
    runtimeOnly 'io.micrometer:micrometer-registry-prometheus'

    // Lombok (optional, for cleaner code)
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'

    // Testing
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation 'org.springframework.security:spring-security-test'
    testImplementation platform("org.testcontainers:testcontainers-bom:${testcontainersVersion}")
    testImplementation 'org.testcontainers:testcontainers'
    testImplementation 'org.testcontainers:postgresql'
    testImplementation 'org.testcontainers:junit-jupiter'
    testImplementation 'io.rest-assured:rest-assured'
    testImplementation 'org.awaitility:awaitility'
}

// Test configuration
tasks.named('test') {
    useJUnitPlatform()
    finalizedBy jacocoTestReport
}

// Integration test configuration
sourceSets {
    integrationTest {
        java {
            compileClasspath += sourceSets.main.output
            runtimeClasspath += sourceSets.main.output
            srcDir file('src/integration-test/java')
        }
        resources.srcDir file('src/integration-test/resources')
    }
}

configurations {
    integrationTestImplementation.extendsFrom testImplementation
    integrationTestRuntimeOnly.extendsFrom testRuntimeOnly
}

task integrationTest(type: Test) {
    description = 'Runs integration tests.'
    group = 'verification'
    testClassesDirs = sourceSets.integrationTest.output.classesDirs
    classpath = sourceSets.integrationTest.runtimeClasspath
    shouldRunAfter test
    useJUnitPlatform()
}

// Jacoco configuration
jacoco {
    toolVersion = "0.8.11"
}

jacocoTestReport {
    dependsOn test
    reports {
        xml.required = true
        html.required = true
        csv.required = false
    }
}

// OWASP Dependency Check
dependencyCheck {
    failBuildOnCVSS = 7
    suppressionFile = 'dependency-check-suppressions.xml'
}

// SonarQube
sonar {
    properties {
        property "sonar.projectKey", "order-service"
        property "sonar.projectName", "Order Service"
        property "sonar.coverage.jacoco.xmlReportPaths", "${buildDir}/reports/jacoco/test/jacocoTestReport.xml"
    }
}
```



### Dependencies (build.gradle) 2 CHECK
```gradle
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.4.0'
    id 'io.spring.dependency-management' version '1.1.4'
    id 'jacoco'
    id 'org.owasp.dependencycheck' version '9.0.0'
    id 'org.sonarqube' version '4.4.1.3373'
}

group = 'com.example'
version = '0.0.1-SNAPSHOT'

java {
    sourceCompatibility = '25'
}

configurations {
    compileOnly {
        extendsFrom annotationProcessor
    }
}

repositories {
    mavenCentral()
}

ext {
    set('testcontainersVersion', "1.19.3")
    set('resilience4jVersion', "2.2.0")
    set('opentelemetryVersion', "1.34.1")
}

dependencies {
    // Spring Boot
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-cache'
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
    implementation 'org.springframework.boot:spring-boot-starter-security'
    implementation 'org.springframework.boot:spring-boot-starter-oauth2-resource-server'
    implementation 'org.springframework.boot:spring-boot-starter-validation'

    // OpenTelemetry
    implementation platform("io.opentelemetry:opentelemetry-bom:${opentelemetryVersion}")
    implementation 'io.opentelemetry:opentelemetry-api'
    implementation 'io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter'

    // Resilience4j
    implementation platform("io.github.resilience4j:resilience4j-bom:${resilience4jVersion}")
    implementation 'io.github.resilience4j:resilience4j-spring-boot3'
    implementation 'io.github.resilience4j:resilience4j-circuitbreaker'
    implementation 'io.github.resilience4j:resilience4j-retry'
    implementation 'io.github.resilience4j:resilience4j-bulkhead'
    implementation 'io.github.resilience4j:resilience4j-timelimiter'

    // Caching
    implementation 'org.springframework.boot:spring-boot-starter-data-redis'
    implementation 'io.lettuce:lettuce-core'

    // Database
    runtimeOnly 'org.postgresql:postgresql'
    implementation 'org.flywaydb:flyway-core'
    implementation 'org.flywaydb:flyway-database-postgresql'

    // Observability
    runtimeOnly 'io.micrometer:micrometer-registry-prometheus'

    // Lombok (optional, for cleaner code)
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'

    // Testing
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation 'org.springframework.security:spring-security-test'
    testImplementation platform("org.testcontainers:testcontainers-bom:${testcontainersVersion}")
    testImplementation 'org.testcontainers:testcontainers'
    testImplementation 'org.testcontainers:postgresql'
    testImplementation 'org.testcontainers:junit-jupiter'
    testImplementation 'io.rest-assured:rest-assured'
    testImplementation 'org.awaitility:awaitility'
}

// Test configuration
tasks.named('test') {
    useJUnitPlatform()
    finalizedBy jacocoTestReport
}

// Integration test configuration
sourceSets {
    integrationTest {
        java {
            compileClasspath += sourceSets.main.output
            runtimeClasspath += sourceSets.main.output
            srcDir file('src/integration-test/java')
        }
        resources.srcDir file('src/integration-test/resources')
    }
}

configurations {
    integrationTestImplementation.extendsFrom testImplementation
    integrationTestRuntimeOnly.extendsFrom testRuntimeOnly
}

task integrationTest(type: Test) {
    description = 'Runs integration tests.'
    group = 'verification'
    testClassesDirs = sourceSets.integrationTest.output.classesDirs
    classpath = sourceSets.integrationTest.runtimeClasspath
    shouldRunAfter test
    useJUnitPlatform()
}

// Jacoco configuration
jacoco {
    toolVersion = "0.8.11"
}

jacocoTestReport {
    dependsOn test
    reports {
        xml.required = true
        html.required = true
        csv.required = false
    }
}

// OWASP Dependency Check
dependencyCheck {
    failBuildOnCVSS = 7
    suppressionFile = 'dependency-check-suppressions.xml'
}

// SonarQube
sonar {
    properties {
        property "sonar.projectKey", "order-service"
        property "sonar.projectName", "Order Service"
        property "sonar.coverage.jacoco.xmlReportPaths", "${buildDir}/reports/jacoco/test/jacocoTestReport.xml"
    }
}
```

## Conclusion

This architecture provides a solid foundation for building production-ready, cloud-native microservices with:
- Clean domain-driven design
- Comprehensive observability
- High availability and scalability
- Resilience patterns
- Security best practices
- Automated testing and deployment

Adapt these guidelines to your specific business requirements while maintaining the core principles of clean architecture and cloud-native design.