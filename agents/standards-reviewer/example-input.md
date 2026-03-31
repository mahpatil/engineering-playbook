# Example Input: PR Diff with Deliberate Violations

## Request

Review the following PR diff for violations of `all` standards. The PR is adding infrastructure Terraform for a new `orders-api` staging environment and updating its Kubernetes deployment manifest.

```
standards_scope: all
input_type: pr-diff
pr_url: https://github.com/acme/orders-api/pull/17
author: dev-engineer
```

---

## PR Diff

```diff
diff --git a/infra/orders-api/staging/main.tf b/infra/orders-api/staging/main.tf
new file mode 100644
--- /dev/null
+++ b/infra/orders-api/staging/main.tf
@@ -0,0 +1,58 @@
+terraform {
+  required_providers {
+    aws = {
+      source  = "hashicorp/aws"
+      version = ">= 4.0"
+    }
+  }
+  backend "local" {}
+}
+
+provider "aws" {
+  region = "us-east-1"
+}
+
+resource "aws_security_group" "orders_api" {
+  name        = "orders-api-sg"
+  description = "Orders API security group"
+  vpc_id      = "vpc-0abc1234def56789"
+
+  ingress {
+    from_port   = 8080
+    to_port     = 8080
+    protocol    = "tcp"
+    cidr_blocks = ["0.0.0.0/0"]
+  }
+
+  egress {
+    from_port   = 0
+    to_port     = 0
+    protocol    = "-1"
+    cidr_blocks = ["0.0.0.0/0"]
+  }
+}
+
+resource "aws_db_instance" "orders" {
+  identifier           = "orders-staging"
+  engine               = "postgres"
+  engine_version       = "15.4"
+  instance_class       = "db.t3.micro"
+  allocated_storage    = 20
+  db_name              = "orders"
+  username             = "admin"
+  password             = "SuperSecret123!"
+  publicly_accessible  = true
+  skip_final_snapshot  = true
+}
+
+# Tags intentionally omitted for brevity
diff --git a/k8s/orders-api/staging/deployment.yaml b/k8s/orders-api/staging/deployment.yaml
new file mode 100644
--- /dev/null
+++ b/k8s/orders-api/staging/deployment.yaml
@@ -0,0 +1,42 @@
+apiVersion: apps/v1
+kind: Deployment
+metadata:
+  name: orders-api
+  namespace: staging
+spec:
+  replicas: 1
+  selector:
+    matchLabels:
+      app: orders-api
+  template:
+    metadata:
+      labels:
+        app: orders-api
+    spec:
+      containers:
+        - name: orders-api
+          image: us-central1-docker.pkg.dev/acme-project/apps/orders-api:latest
+          ports:
+            - containerPort: 8080
+          env:
+            - name: DB_PASSWORD
+              value: "SuperSecret123!"
diff --git a/src/main/java/com/acme/orders/OrderController.java b/src/main/java/com/acme/orders/OrderController.java
new file mode 100644
--- /dev/null
+++ b/src/main/java/com/acme/orders/OrderController.java
@@ -0,0 +1,30 @@
+@RestController
+@RequestMapping("/orders")
+public class OrderController {
+
+    @Autowired
+    private OrderService orderService;
+
+    @GetMapping
+    public List<OrderResponse> listOrders(
+            @RequestParam(defaultValue = "0") int page,
+            @RequestParam(defaultValue = "20") int size) {
+        return orderService.findAll(page, size);
+    }
+
+    @PostMapping
+    public ResponseEntity<OrderResponse> createOrder(@RequestBody CreateOrderRequest req) {
+        try {
+            Order order = orderService.create(req);
+            return ResponseEntity.ok(new OrderResponse(order));
+        } catch (Exception e) {
+            return ResponseEntity.internalServerError()
+                .body(new OrderResponse("error: " + e.getMessage()));
+        }
+    }
+}
```

---

## Violations Planted in This Diff

For illustration only — the agent should identify these independently:

1. **`main.tf` line 8** — `backend "local" {}` used for staging (should be remote).
2. **`main.tf` line 24** — Security group allows `0.0.0.0/0` ingress on port 8080 for a compute resource.
3. **`main.tf` line 39–43** — RDS password hard-coded as plain text; `publicly_accessible = true` on a database.
4. **`deployment.yaml` line 19** — `image: ...:latest` tag used.
5. **`deployment.yaml`** — Missing `securityContext`, `resources`, `readinessProbe`, `livenessProbe`.
6. **`OrderController.java` line 8** — Field injection `@Autowired` instead of constructor injection.
7. **`OrderController.java` line 13** — Offset/limit pagination instead of cursor-based.
8. **`OrderController.java` line 24** — Error response returns a plain string, not RFC 9457 `ProblemDetails`.

## Expected Review Output

A Markdown report containing:
- **4 CRITICAL** findings (plain-text DB password, public DB, 0.0.0.0/0 compute ingress, missing security contexts).
- **3 HIGH** findings (local backend, latest image tag, missing resource limits).
- **2 MEDIUM** findings (offset pagination, field injection).
- **1 LOW** finding (plain error string in response — upgradeable to HIGH if API standard is in scope).
- A summary section listing passed checks (e.g. Terraform provider declared, namespace present).
