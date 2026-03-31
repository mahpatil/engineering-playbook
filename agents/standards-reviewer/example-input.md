# standards-reviewer — Example Input

## Invocation

Review a PR diff that adds a payment processing endpoint to the order service. The diff contains several intentional violations for demonstration purposes.

---

## Request

```
REVIEW_TYPE: diff
LANGUAGE: java
CONTEXT: Adding a payment processing endpoint that integrates with an external Stripe payment gateway. This is a revenue-critical path change.

DIFF:
diff --git a/src/main/java/com/acme/orders/infrastructure/config/StripeConfig.java b/src/main/java/com/acme/orders/infrastructure/config/StripeConfig.java
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/src/main/java/com/acme/orders/infrastructure/config/StripeConfig.java
@@ -0,0 +1,18 @@
+package com.acme.orders.infrastructure.config;
+
+import com.stripe.Stripe;
+import org.springframework.context.annotation.Configuration;
+import jakarta.annotation.PostConstruct;
+
+@Configuration
+public class StripeConfig {
+
+    @PostConstruct
+    public void init() {
+        // TODO: move to env var before prod — VIOLATION: secret is currently hardcoded below
+        Stripe.apiKey = System.getProperty("stripe.api.key", "sk_test_PLACEHOLDER_REPLACE_WITH_SECRET_MANAGER");
+    }
+}

diff --git a/src/main/java/com/acme/orders/api/PaymentController.java b/src/main/java/com/acme/orders/api/PaymentController.java
new file mode 100644
index 0000000..def5678
--- /dev/null
+++ b/src/main/java/com/acme/orders/api/PaymentController.java
@@ -0,0 +1,62 @@
+package com.acme.orders.api;
+
+import com.acme.orders.domain.Order;
+import com.acme.orders.infrastructure.persistence.OrderJpaRepository;
+import com.acme.orders.infrastructure.stripe.StripePaymentService;
+import com.stripe.exception.StripeException;
+import org.springframework.web.bind.annotation.*;
+import org.slf4j.Logger;
+import org.slf4j.LoggerFactory;
+
+@RestController
+@RequestMapping("/payments")
+public class PaymentController {
+
+    @Autowired
+    private OrderJpaRepository orderRepo;
+
+    @Autowired
+    private StripePaymentService stripeService;
+
+    private static final Logger log = LoggerFactory.getLogger(PaymentController.class);
+
+    @PostMapping("/processPayment/{orderId}")
+    public Map<String, Object> processPayment(@PathVariable String orderId,
+                                               @RequestParam String cardNumber,
+                                               @RequestParam String cvv) {
+        try {
+            Order order = orderRepo.findById(UUID.fromString(orderId)).get();
+            log.info("Processing payment for order " + orderId +
+                     " customer: " + order.getCustomerEmail() +
+                     " card: " + cardNumber);
+
+            var charge = stripeService.charge(order.getTotal(), cardNumber, cvv);
+
+            order.setStatus("CONFIRMED");
+            orderRepo.save(order);
+
+            return Map.of("success", true, "chargeId", charge.getId());
+        } catch (Exception e) {
+            log.error("Payment failed");
+            return Map.of("success", false, "error", e.getMessage());
+        }
+    }
+
+    @GetMapping("/getPaymentHistory")
+    public List<Map<String, Object>> getPaymentHistory(@RequestParam String customerId) {
+        return orderRepo.findAll().stream()
+            .filter(o -> o.getCustomerId().equals(customerId))
+            .map(o -> Map.of(
+                "orderId", o.getId(),
+                "amount", o.getTotal().getAmount().doubleValue(),
+                "status", o.getStatus()
+            ))
+            .collect(Collectors.toList());
+    }
+}

diff --git a/src/main/java/com/acme/orders/domain/Order.java b/src/main/java/com/acme/orders/domain/Order.java
+++ b/src/main/java/com/acme/orders/domain/Order.java
@@ -1,6 +1,8 @@
 package com.acme.orders.domain;

+import com.acme.orders.infrastructure.persistence.OrderJpaRepository;
+
 public class Order {
```

---

## Violations Demonstrated in This Diff

This example intentionally includes the following violations for demonstration purposes (the agent should find all of them):

**CRITICAL:**
- `CRIT-001`: API key sourced from system property with a fallback literal — secrets must come exclusively from the cloud secrets manager, never via fallback literals in code
- `CRIT-002`: Card number and CVV passed as query parameters — credentials in URLs appear in access logs, browser history, and proxy logs (PCI-DSS violation)
- `CRIT-003`: Customer email and raw `cardNumber` logged in an INFO statement — PII logged without masking

**HIGH:**
- `HIGH-001`: `PaymentController` directly imports and uses `OrderJpaRepository` (infrastructure adapter) — API layer bypassing the application/use case layer (architecture violation)
- `HIGH-002`: `Order.java` imports from `infrastructure.persistence` — domain layer depending on infrastructure
- `HIGH-003`: `@Autowired` field injection on `orderRepo` and `stripeService` — constructor injection required
- `HIGH-004`: Exception caught silently — `catch (Exception e)` logs `"Payment failed"` with no context, then returns `e.getMessage()` leaking internal detail to the caller
- `HIGH-005`: No circuit breaker around Stripe call — unprotected external service call with no Resilience4j wrapper
- `HIGH-006`: `orderRepo.findAll()` used to filter in memory — unbounded database query

**MEDIUM:**
- `MED-001`: URL `/payments/processPayment/{orderId}` uses camelCase and a verb — should be `/api/v1/orders/{orderId}/payment-charges`
- `MED-002`: Response shape `Map<String, Object>` with `"success": false` — not RFC 9457 Problem Details format
- `MED-003`: No `/api/v1/` prefix or version in path mapping
- `MED-004`: Monetary amount returned as `doubleValue()` — floating-point for money is incorrect; must be string

**LOW:**
- `LOW-001`: No `@Operation` / `@ApiResponse` annotations — endpoint not documented in OpenAPI spec
- `LOW-002`: Unstructured log statement using string concatenation — should use structured key/value pairs

**Expected Verdict:** BLOCK (multiple CRITICAL and HIGH findings)
```
