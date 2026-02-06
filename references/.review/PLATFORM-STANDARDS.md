# Platform Standards

Standards for platform-level infrastructure and cross-cutting concerns.

---

## Service Mesh & Network Security

### Service Mesh Selection
| Option | Use Case | Considerations |
|--------|----------|----------------|
| Istio | Full-featured, enterprise | Higher resource overhead |
| Linkerd | Lightweight, simple | Fewer features, lower overhead |
| Cilium | eBPF-based, high performance | Requires Linux kernel 4.9+ |

### mTLS Configuration
All service-to-service communication must use mutual TLS:
- Automatic certificate rotation
- Service identity verification
- Encrypted traffic in transit

### Traffic Management
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: order-service
spec:
  hosts:
    - order-service
  http:
    - route:
        - destination:
            host: order-service
            subset: v1
          weight: 90
        - destination:
            host: order-service
            subset: v2
          weight: 10
      retries:
        attempts: 3
        perTryTimeout: 2s
        retryOn: 5xx,reset,connect-failure
```

---

## API Gateway

### Responsibilities
- Rate limiting and throttling at edge
- Request/response transformation
- Authentication/authorization
- API composition for BFF patterns
- Request routing and load balancing
- API versioning

### Configuration Example
```yaml
# Spring Cloud Gateway configuration
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates:
            - Path=/api/v1/orders/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 100
                redis-rate-limiter.burstCapacity: 200
            - name: CircuitBreaker
              args:
                name: orderServiceCB
                fallbackUri: forward:/fallback/orders
```

### API Versioning Strategy
- URL path versioning: `/api/v1/orders`, `/api/v2/orders`
- Support N-1 versions minimum during transitions
- Deprecation notices 90 days before removal
- OpenAPI specification required for all endpoints

---

## Kubernetes Configuration

### PodDisruptionBudget
Ensure availability during voluntary disruptions:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: order-service-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: order-service
```

### NetworkPolicy
Restrict pod-to-pod communication:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: order-service-network-policy
spec:
  podSelector:
    matchLabels:
      app: order-service
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-gateway
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
```

### Topology Spread Constraints
Ensure zone-aware scheduling:
```yaml
spec:
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: order-service
```

### Resource Configuration
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### Health Probes
```yaml
livenessProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
  initialDelaySeconds: 20
  periodSeconds: 5
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 30
```

---

## Event Infrastructure

### Message Broker Selection
| Broker | Use Case | Considerations |
|--------|----------|----------------|
| Kafka | High throughput, event streaming | Complex operations, higher overhead |
| GCP Pub/Sub | Cloud-native, managed | GCP-specific, simpler operations |
| RabbitMQ | Traditional messaging, routing | Lower throughput than Kafka |

### Schema Registry
- Use Avro or Protobuf for schema definition
- Schema evolution with backward/forward compatibility
- Central registry for all event schemas
- Automated compatibility checking in CI/CD

### Dead Letter Queue Configuration
```yaml
# GCP Pub/Sub
deadLetterPolicy:
  deadLetterTopic: projects/PROJECT_ID/topics/orders-dlq
  maxDeliveryAttempts: 5

# Kafka
spring:
  kafka:
    consumer:
      properties:
        max.poll.interval.ms: 300000
    listener:
      ack-mode: RECORD
```

### Idempotency
- Include unique event ID in all messages
- Store processed event IDs with TTL
- Use idempotency keys for write operations

---

## Database High Availability

### Primary/Replica Configuration
- Synchronous replication for critical data
- Asynchronous replication for read scaling
- Automatic failover with health checks

### Connection Pooling
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20
      minimum-idle: 10
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000
```

### Read Replica Routing
```java
@Configuration
public class DataSourceConfig {
    @Bean
    @Primary
    public DataSource routingDataSource(
            @Qualifier("primaryDataSource") DataSource primary,
            @Qualifier("replicaDataSource") DataSource replica) {
        var routingDataSource = new RoutingDataSource();
        routingDataSource.setDefaultTargetDataSource(primary);
        routingDataSource.setTargetDataSources(Map.of(
            DataSourceType.PRIMARY, primary,
            DataSourceType.REPLICA, replica
        ));
        return routingDataSource;
    }
}
```

---

## Multi-Tenancy Patterns

### Isolation Strategies
| Strategy | Isolation | Complexity | Cost |
|----------|-----------|------------|------|
| Database per tenant | Highest | High | High |
| Schema per tenant | High | Medium | Medium |
| Row-level (tenant_id) | Low | Low | Low |

### Tenant Context Propagation
```java
@Component
public class TenantFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request,
            HttpServletResponse response, FilterChain chain) {
        String tenantId = request.getHeader("X-Tenant-ID");
        TenantContext.setCurrentTenant(tenantId);
        try {
            chain.doFilter(request, response);
        } finally {
            TenantContext.clear();
        }
    }
}
```

### Resource Quotas
- CPU/memory limits per tenant
- Rate limiting per tenant
- Storage quotas
- API call limits

---

## Disaster Recovery

### RTO/RPO Requirements
| Tier | RTO | RPO | Example Services |
|------|-----|-----|------------------|
| Critical | < 1 hour | < 5 min | Payment, Auth |
| Important | < 4 hours | < 1 hour | Orders, Inventory |
| Standard | < 24 hours | < 4 hours | Reporting, Analytics |

### Backup Strategy
- Automated daily backups with retention policy
- Cross-region replication for critical data
- Regular restore testing (monthly minimum)
- Point-in-time recovery capability

### Runbook Requirements
- Document all recovery procedures
- Include contact escalation paths
- Test runbooks quarterly
- Update after every incident

---

## Chaos Engineering

### Failure Scenarios to Test
- Pod failures and restarts
- Network partitions between services
- Database connection failures
- Cache unavailability
- External service timeouts
- Zone/region failures

### Tools
| Tool | Platform | Use Case |
|------|----------|----------|
| Chaos Monkey | Kubernetes | Random pod termination |
| Litmus Chaos | Kubernetes | Comprehensive experiments |
| Chaos Mesh | Kubernetes | Network, I/O, time chaos |
| Gremlin | Multi-platform | Enterprise chaos platform |

### Game Day Schedule
- Monthly chaos experiments in non-production
- Quarterly production chaos (controlled)
- Post-incident chaos validation

---

## Configuration Management

### ConfigMaps vs External Configuration
| Approach | Use When | Avoid When |
|----------|----------|------------|
| ConfigMaps | Static config, K8s native | Frequent changes, secrets |
| Spring Cloud Config | Dynamic refresh, versioned | Simple deployments |
| Consul | Service discovery + config | Overkill for small systems |

### Environment-Specific Configuration
```yaml
# application.yml (base)
spring:
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:local}

# application-local.yml
spring:
  datasource:
    url: jdbc:h2:mem:testdb

# application-production.yml
spring:
  datasource:
    url: jdbc:postgresql://${DB_HOST}:5432/${DB_NAME}
```

### Immutable Configuration
- Configuration changes trigger new deployments
- No runtime configuration mutation
- Version control all configuration
- Audit trail for all changes
