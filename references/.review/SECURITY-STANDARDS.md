# Security Standards

Comprehensive security standards for cloud-native applications.

---

## Zero Trust Principles

### Core Tenets
1. **Never trust, always verify** - Authenticate every request
2. **Assume breach** - Design as if perimeter is already compromised
3. **Least privilege** - Minimum access necessary for function
4. **Micro-segmentation** - Isolate workloads and data

### Implementation Requirements
- mTLS for all service-to-service communication
- Token-based authentication for all APIs
- Network policies restricting pod communication
- Encrypted data at rest and in transit

---

## Authentication & Authorization

### OAuth2/JWT Configuration
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
            .sessionManagement(session -> session
                .sessionCreationPolicy(SessionCreationPolicy.STATELESS)
            )
            .csrf(csrf -> csrf.disable()) // Stateless API
            .headers(headers -> headers
                .contentSecurityPolicy(csp ->
                    csp.policyDirectives("default-src 'self'"))
                .frameOptions(frame -> frame.deny())
                .xssProtection(xss -> xss.disable()) // Modern browsers
                .contentTypeOptions(Customizer.withDefaults())
            );

        return http.build();
    }

    private Converter<Jwt, AbstractAuthenticationToken> jwtConverter() {
        var converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            var roles = jwt.getClaimAsStringList("roles");
            return roles.stream()
                .map(role -> new SimpleGrantedAuthority("ROLE_" + role))
                .collect(Collectors.toList());
        });
        return converter;
    }
}
```

### Method-Level Security
```java
@Service
public class OrderService {

    @PreAuthorize("hasRole('USER')")
    public Order createOrder(CreateOrderCommand command) {
        // ...
    }

    @PreAuthorize("hasRole('ADMIN') or @orderSecurity.isOwner(#orderId)")
    public Order getOrder(OrderId orderId) {
        // ...
    }

    @PreAuthorize("hasRole('ADMIN')")
    public void deleteOrder(OrderId orderId) {
        // ...
    }
}
```

---

## Secrets Management

### Principles
- Never hardcode secrets in code or configuration
- Use external secret management (Vault, GCP Secret Manager)
- Automatic rotation for all secrets
- Audit logging for secret access

### GCP Secret Manager Integration
```java
@Configuration
public class SecretConfig {

    @Value("${sm://projects/PROJECT/secrets/db-password/versions/latest}")
    private String dbPassword;
}
```

### Kubernetes External Secrets
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: gcp-secret-store
    kind: ClusterSecretStore
  target:
    name: db-credentials
  data:
    - secretKey: password
      remoteRef:
        key: projects/PROJECT_ID/secrets/db-password
```

### Secret Rotation
- Database credentials: 90-day rotation
- API keys: 180-day rotation
- Service account keys: 365-day rotation
- JWT signing keys: On-demand with overlap period

---

## Service-to-Service Security

### mTLS Configuration
```yaml
# Istio PeerAuthentication
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT

# AuthorizationPolicy
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: order-service-policy
spec:
  selector:
    matchLabels:
      app: order-service
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/production/sa/api-gateway"]
      to:
        - operation:
            methods: ["GET", "POST"]
            paths: ["/api/v1/orders/*"]
```

### Service Identity
- Each service has unique identity (ServiceAccount)
- Identity verified via mTLS certificates
- Authorization based on service identity

---

## Input Validation

### API Input Validation
```java
public record CreateOrderRequest(
    @NotNull(message = "Customer ID is required")
    UUID customerId,

    @NotEmpty(message = "At least one order line required")
    @Size(max = 100, message = "Maximum 100 order lines")
    List<@Valid OrderLineRequest> orderLines
) {}

public record OrderLineRequest(
    @NotNull UUID productId,

    @Min(value = 1, message = "Quantity must be at least 1")
    @Max(value = 1000, message = "Quantity cannot exceed 1000")
    int quantity
) {}

@RestController
public class OrderController {
    @PostMapping("/api/v1/orders")
    public ResponseEntity<Order> createOrder(
            @Valid @RequestBody CreateOrderRequest request) {
        // Request is validated before reaching here
    }
}
```

### SQL Injection Prevention
- Always use parameterized queries
- Never concatenate user input into SQL
- Use JPA/Hibernate with proper entity mapping

```java
// CORRECT: Parameterized query
@Query("SELECT o FROM Order o WHERE o.customerId = :customerId")
List<Order> findByCustomerId(@Param("customerId") UUID customerId);

// WRONG: String concatenation (vulnerable)
// "SELECT * FROM orders WHERE customer_id = '" + customerId + "'"
```

---

## Supply Chain Security

### Dependency Scanning
```gradle
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

### Container Image Scanning
```yaml
# GitHub Actions
- name: Trivy Container Scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.IMAGE }}
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'
```

### SBOM Generation
- Generate Software Bill of Materials for all releases
- Include in container image labels
- Store in artifact registry

### Image Signing
```bash
# Sign with Cosign
cosign sign --key cosign.key ${IMAGE}

# Verify signature
cosign verify --key cosign.pub ${IMAGE}
```

---

## Compliance & Governance

### Policy-as-Code (OPA/Kyverno)
```yaml
# Kyverno policy: require resource limits
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: enforce
  rules:
    - name: check-limits
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "Resource limits are required"
        pattern:
          spec:
            containers:
              - resources:
                  limits:
                    memory: "?*"
                    cpu: "?*"
```

### Audit Logging
```java
@Aspect
@Component
public class AuditAspect {

    private static final Logger auditLog =
        LoggerFactory.getLogger("AUDIT");

    @Around("@annotation(audited)")
    public Object audit(ProceedingJoinPoint pjp, Audited audited)
            throws Throwable {
        var principal = SecurityContextHolder.getContext()
            .getAuthentication().getName();
        var action = audited.action();

        auditLog.info("action={} user={} method={} args={}",
            action, principal,
            pjp.getSignature().getName(),
            Arrays.toString(pjp.getArgs()));

        return pjp.proceed();
    }
}
```

### Data Classification
| Classification | Examples | Handling |
|----------------|----------|----------|
| Public | Marketing content | No restrictions |
| Internal | Internal docs | Authentication required |
| Confidential | Customer data | Encryption, audit logging |
| Restricted | PII, financial | Encryption, access control, audit, DLP |

---

## Security Testing

### SAST (Static Analysis)
```yaml
# SonarQube in CI
- name: SonarQube Scan
  run: |
    ./gradlew sonar \
      -Dsonar.host.url=${{ secrets.SONAR_URL }} \
      -Dsonar.token=${{ secrets.SONAR_TOKEN }}
```

### DAST (Dynamic Analysis)
- OWASP ZAP for API security testing
- Run against staging environment
- Include in release gate

### Security Test Examples
```java
@SpringBootTest
@AutoConfigureMockMvc
class SecurityTest {

    @Test
    void shouldRejectUnauthenticatedRequests() throws Exception {
        mockMvc.perform(get("/api/v1/orders"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void shouldRejectInvalidToken() throws Exception {
        mockMvc.perform(get("/api/v1/orders")
                .header("Authorization", "Bearer invalid"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void shouldPreventSqlInjection() throws Exception {
        mockMvc.perform(get("/api/v1/orders")
                .param("customerId", "'; DROP TABLE orders; --"))
            .andExpect(status().isBadRequest());
    }

    @Test
    @WithMockUser(roles = "USER")
    void shouldEnforceRateLimiting() throws Exception {
        for (int i = 0; i < 100; i++) {
            mockMvc.perform(get("/api/v1/orders"));
        }
        mockMvc.perform(get("/api/v1/orders"))
            .andExpect(status().isTooManyRequests());
    }
}
```

---

## Security Headers

### Required Headers
```yaml
# Response headers
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=()
```

### CORS Configuration
```java
@Configuration
public class CorsConfig {
    @Bean
    public CorsFilter corsFilter() {
        var config = new CorsConfiguration();
        config.setAllowedOrigins(List.of(
            "https://app.example.com"
        ));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
        config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
        config.setMaxAge(3600L);

        var source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return new CorsFilter(source);
    }
}
```
