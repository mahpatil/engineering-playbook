# API Design Standards
Applicaton Programming Interface is set of rules and formats that a software system exposes for other software applications to consume,
without those applications needing to understand how the system was built. They promote reuse, interoperability, reduce complexity.

The document covers the standards for designing, versioning, and operating APIs that are consistent, evolvable, and developer-friendly; and mainly focuses on Web/HTTPs based APIs exposed over the internet and assume JSON objects primarily.

---

## Key Business Drivers

| Driver | Outcome |
|--------|---------|
| **Developer Experience** | Consistent, predictable APIs reduce integration time and support costs |
| **Time to Market** | API-first design enables parallel frontend and backend development |
| **Partner & Ecosystem Enablement** | Well-designed APIs unlock third-party integrations and revenue streams |
| **Evolvability** | Versioned, backward-compatible APIs allow systems to evolve without breaking consumers |
| **Operational Efficiency** | Standardized patterns reduce cognitive load across teams and simplify tooling |
| **Security & Compliance** | Consistent authentication, authorization, and data handling patterns reduce breach risk |
| **Observability** | Standardized error and logging formats enable faster incident diagnosis |

---

## Core Principles

### 1. API-First Design
Define the API contract before writing implementation code. The contract is the product — consumers depend on it, not on internal implementation details.

**What this means:**
- Write OpenAPI (REST) or AsyncAPI (events) specs before writing service code
- Review the API contract with consumers before implementation begins
- Generate server stubs and client SDKs from the contract — do not write them by hand
- The spec is the single source of truth; code must conform to it, not the reverse
- Store API specs in source control alongside the service code

**Example:** Before building a new `inventory-service`, draft the OpenAPI spec for `GET /inventory/{sku}` and `POST /inventory/reserve`. Review it with dependent teams. Then implement.

---

### 2. RESTful Resource Modeling
Design APIs around resources (nouns), not actions (verbs). HTTP methods express the action; the URL names the resource.

**What this means:**
- URLs identify resources: `/orders`, `/orders/{id}`, `/orders/{id}/items`
- HTTP methods carry intent:
  - `GET` — retrieve, never mutate state
  - `POST` — create a new resource or trigger an action
  - `PUT` — replace a resource entirely
  - `PATCH` — partial update
  - `DELETE` — remove a resource
- Resources are plural nouns: `/users`, not `/user` or `/getUsers`
- Nest resources to express ownership: `/orders/{orderId}/items`, not `/order-items?orderId=`
- Keep nesting to two levels maximum — deeper nesting becomes unwieldy

**URL patterns:**
| Action | Method | URL |
|--------|--------|-----|
| List orders | GET | `/orders` |
| Get single order | GET | `/orders/{id}` |
| Create order | POST | `/orders` |
| Update order status | PATCH | `/orders/{id}` |
| Cancel order | DELETE | `/orders/{id}` |
| List items in order | GET | `/orders/{id}/items` |

---

### 3. Consistent Response Structure
All API responses follow a predictable envelope structure. Consumers should not need to reverse-engineer each endpoint's response format.

**Success response:**
```json
{
  "data": { ... },
  "meta": {
    "requestId": "uuid",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

**Collection response (paginated):**
```json
{
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "totalItems": 150,
    "totalPages": 8
  },
  "meta": {
    "requestId": "uuid",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

**Error response:**
```json
{
  "error": {
    "code": "ORDER_NOT_FOUND",
    "message": "Order with ID 12345 was not found",
    "details": [ ... ],
    "requestId": "uuid",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

**What this means:**
- Never return raw arrays at the top level — always wrap in an object
- Always include `requestId` for traceability
- Machine-readable `code` fields in errors, human-readable `message`
- `details` array for validation errors listing field-level issues

---

### 4. HTTP Status Codes Used Correctly
Use standard HTTP status codes with their intended semantics. Do not return `200 OK` with an error body.

| Code | When to Use |
|------|-------------|
| 200 OK | Successful GET, PATCH, PUT |
| 201 Created | Successful POST that creates a resource |
| 204 No Content | Successful DELETE or action with no response body |
| 400 Bad Request | Invalid request body or parameters (validation failure) |
| 401 Unauthorized | Missing or invalid authentication credentials |
| 403 Forbidden | Authenticated but not authorized for this resource |
| 404 Not Found | Resource does not exist |
| 409 Conflict | State conflict (e.g., duplicate creation, optimistic lock) |
| 422 Unprocessable Entity | Semantically invalid request (passes schema but fails business rules) |
| 429 Too Many Requests | Rate limit exceeded — include `Retry-After` header |
| 500 Internal Server Error | Unexpected server-side failure |
| 503 Service Unavailable | Service temporarily unavailable — include `Retry-After` |

**Anti-pattern:** Returning `200 OK` with `{"success": false}` in the body. Use the correct 4xx or 5xx code.

---

### 5. Versioning Strategy
APIs are versioned to allow evolution without breaking existing consumers. Versioning is in the URL path.

**What this means:**
- Version prefix in the URL: `/api/v1/orders`, `/api/v2/orders`
- A new major version is required for any breaking change
- Non-breaking changes (adding optional fields, new endpoints) do not require a new version
- Support at minimum two versions simultaneously during transition periods
- Deprecated versions have a published sunset date communicated via `Deprecation` and `Sunset` response headers
- Never silently remove or change the behavior of a published version

**Breaking changes (require new version):**
- Removing a field or endpoint
- Changing a field's type or format
- Changing required/optional status of a field
- Modifying error codes or response structure

**Non-breaking changes (no new version needed):**
- Adding new optional request fields
- Adding new response fields
- Adding new endpoints
- Adding new enum values (when consumers are designed to ignore unknown values)

---

### 6. Authentication and Authorization
All APIs require authentication. Authorization is enforced at the resource level. Never trust a request without verifying identity and permissions.

**What this means:**
- External APIs: OAuth 2.0 with JWT bearer tokens (`Authorization: Bearer <token>`)
- Service-to-service: mTLS or short-lived service tokens via a service mesh
- Validate the JWT on every request — do not cache validation results beyond token TTL
- Enforce authorization at the resource level: a user can only access their own data
- Scope claims in the token define what operations are permitted
- API keys for machine-to-machine integrations without user context — rotate on schedule

**Authorization model:**
- Authenticate first (who are you?)
- Then authorize (are you allowed to do this to this resource?)
- Return `401` for authentication failure, `403` for authorization failure — never conflate them

---

### 7. Input Validation and Sanitization
Validate all inputs at the API boundary. Never trust caller-provided data. Reject invalid input early with a clear, actionable error response.

**What this means:**
- Validate all path parameters, query parameters, and request body fields
- Return `400` with field-level details for validation failures
- Reject unexpected fields rather than silently ignoring them (strict mode)
- Sanitize string inputs to prevent injection attacks (XSS, SQL injection)
- Enforce maximum lengths on all string inputs
- Validate content types: reject requests where `Content-Type` does not match the expected format

**Validation error response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "field": "email", "message": "Invalid email format" },
      { "field": "amount", "message": "Must be greater than 0" }
    ],
    "requestId": "uuid"
  }
}
```

---

### 8. Pagination, Filtering, and Sorting
Collection endpoints support pagination, filtering, and sorting through consistent, standardized query parameters.

**Pagination (cursor-based preferred for large datasets):**
```
GET /orders?limit=20&cursor=eyJpZCI6MTAwfQ==
```

**Offset-based pagination (for small, bounded datasets):**
```
GET /orders?page=2&pageSize=20
```

**Filtering:**
```
GET /orders?status=pending&createdAfter=2024-01-01
```

**Sorting:**
```
GET /orders?sortBy=createdAt&sortOrder=desc
```

**What this means:**
- Default page size must be defined and documented (e.g., 20)
- Maximum page size must be enforced (e.g., 100)
- Cursor-based pagination for high-cardinality or real-time datasets
- Offset pagination for admin/reporting use cases with bounded result sets
- Filter parameters use camelCase and match field names in the response
- Sorting defaults are documented — never rely on implicit database ordering

---

### 9. Idempotency
Mutating operations support idempotency to allow safe retries without duplicating effects. This is critical for reliability in distributed systems.

**What this means:**
- `POST` endpoints that create resources accept an `Idempotency-Key` header
- If the same key is submitted twice, return the original response — do not create a duplicate
- `PUT` and `DELETE` are naturally idempotent — design them to be
- Store idempotency keys with a TTL (e.g., 24 hours) — reject expired keys with `422`
- Return the same response body and status code for repeated requests with the same key

**Header:**
```
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

---

### 10. Rate Limiting and Throttling
All public and partner-facing APIs enforce rate limits. Rate limit headers are always returned so consumers can self-regulate.

**What this means:**
- Rate limits are enforced per client (API key or OAuth client ID), not per IP
- Return `429 Too Many Requests` with a `Retry-After` header when limit is exceeded
- Include rate limit headers on every response:
  - `X-RateLimit-Limit`: requests allowed per window
  - `X-RateLimit-Remaining`: requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when the window resets
- Different limits for different tiers (internal, partner, public)
- Burst allowances for short spikes above sustained rate

---

### 11. API Documentation
Every API has complete, accurate, and executable documentation. Consumers should be able to onboard without asking the owning team.

**What this means:**
- OpenAPI 3.x spec is the primary documentation artifact — generated from code annotations or maintained as spec-first
- Every endpoint documents: purpose, request parameters, request body schema, all possible response codes and bodies, authentication requirements
- Provide working `curl` examples for each endpoint
- Developer portal or Swagger UI for interactive exploration
- Changelog maintained for every version — document what changed and when
- Deprecation notices published at least 90 days before sunset

---

### 12. Asynchronous and Event-Driven APIs
For operations that are long-running or trigger cross-service workflows, use asynchronous patterns rather than blocking synchronous responses.

**What this means:**
- Long-running operations return `202 Accepted` with a job/status URL
- Consumers poll the status URL or receive a webhook callback on completion
- Webhooks follow the same authentication and contract standards as REST APIs
- Event schemas documented in AsyncAPI format
- Events are versioned independently of REST APIs

**Async pattern:**
```
POST /reports/generate → 202 Accepted
{
  "jobId": "abc123",
  "statusUrl": "/reports/jobs/abc123",
  "estimatedCompletion": "2024-01-15T10:35:00Z"
}

GET /reports/jobs/abc123 → 200 OK
{
  "data": { "status": "completed", "reportUrl": "/reports/abc123" }
}
```

---
## API Taxonomy

Not all APIs are equal - design decisions, security requirements, versioning commitments, and operational standards differ based on who the consumer is. Classify every API before designing it.

There are five distinct tiers. A common source of confusion is APIs that are **internet-facing but first-party** — reachable from the public internet but consumed exclusively by the organization's own web or mobile apps. These sit between Private and Partner in trust but require public-grade security hardening because they are network-accessible from untrusted environments.

| Dimension | Private | First-Party (BFF) | Partner / Enterprise | Public | Third-Party (Consumed) |
|-----------|---------|-------------------|---------------------|--------|------------------------|
| **Consumer** | Internal services and teams | Org's own web, mobile, or desktop apps | Vetted B2B partners under signed agreement | Any developer or end user | External vendors and SaaS platforms |
| **Network exposure** | Internal network only | Public internet — but no external developer access intended | External, access-controlled (IP allowlist or dedicated gateway route) | Fully public internet | Outbound calls to vendor infrastructure |
| **Trust level** | High — authenticated service identity | Medium-high — controlled app, but running in untrusted environments (browser, device) | Medium — authenticated, contractual, but external | Low — authenticated but untrusted | None — treat as hostile |
| **Auth standard** | mTLS or internal service tokens | Short-lived JWT from auth server + refresh tokens; mobile app attestation (e.g., App Check); PKCE flow for SPAs | OAuth 2.0 client credentials + scoped JWT; optional IP allowlisting | OAuth 2.0 / JWT bearer tokens | API keys, OAuth, or vendor tokens — managed in vault |
| **Versioning commitment** | 30-day windows with team coordination | Flexible — org controls both sides; coordinate with app release cycle | 60-day minimum; governed by contract SLA | 90-day minimum; publicly announced | Vendor-controlled — pin versions; monitor changelogs |
| **Rate limiting** | Generous; quotas for noisy neighbours | Per-user and per-device limits; protect against credential stuffing and scraping | Per-partner quotas defined in commercial agreement | Strict per-client tiered quotas | Respect vendor limits; implement client-side throttling |
| **Documentation** | Internal developer portal or README | Internal only — not published externally | Private portal or shared spec under NDA | Public developer portal with full OpenAPI spec | Internal runbooks for integration patterns and failure modes |
| **Stability expectation** | Evolve freely with team coordination | Flexible — org controls consumers; coordinate with app deployments | High — partners build production systems on these APIs | Highest — breaking changes affect the entire ecosystem | Assume instability — abstract behind an anti-corruption layer |
| **Data exposure** | Full internal models acceptable | Tailored to UI needs (BFF pattern); avoid over-fetching | Scoped to partner's contractual entitlements; no cross-tenant leakage | Minimal — no internal identifiers or infrastructure details | Received data validated and mapped — never passed through raw |
| **SLA** | Best-effort with internal SLOs | High — directly affects user-facing product uptime | Contractual SLA; typically 99.9%+ | Published SLA; tiered by plan | Dependent on vendor SLA — design for unavailability |
| **Onboarding** | Self-service via internal portal | App credentials issued internally; not publicly discoverable | Provisioned by sales/onboarding team | Self-service signup via developer portal | Credentials in vault, provisioned by platform team |

---

### Private APIs
APIs consumed only by services and teams within the same organization. Never reachable from outside the internal network.

**Design considerations:**
- Zero-trust still applies — authenticate all calls with mTLS or internal service tokens
- Consumer-driven contract tests (Pact) enforce schema compatibility before deploy
- Can use richer internal models; not required to minimize payload
- Deprecation windows can be shorter (30 days) with direct team coordination
- Prefer gRPC for high-throughput, latency-sensitive service-to-service calls
- REST acceptable for all other cases
- No need for a public-facing API gateway — internal service mesh handles routing and auth

---

### First-Party APIs (BFF — Backend for Frontend)
APIs exposed over the public internet but intended exclusively for the organization's own web, mobile, or desktop applications. No external developer is expected or permitted to consume them directly.

**Key distinction from Public:** The consumer is known and controlled — the org ships both sides. There is no external developer ecosystem to support, no published SDK, and no public documentation. However, because the API is reachable from untrusted environments (browsers, user devices), it must be hardened as if it were internet-facing.

**Key distinction from Private:** The API crosses a trust boundary — requests originate from code running outside the org's infrastructure, in environments the org does not control. Tokens can be stolen from devices; requests can be replayed or tampered with.

**Design considerations:**
- Use the BFF (Backend for Frontend) pattern — one API tailored to each client type (web BFF, mobile BFF) rather than a generic API serving all clients; this prevents over-fetching and avoids exposing endpoints irrelevant to a given app
- Short-lived JWT access tokens with refresh token rotation; never long-lived tokens on a device or in browser storage
- PKCE (Proof Key for Code Exchange) for Single Page Applications — never use implicit flow
- Mobile app attestation (e.g., Firebase App Check, Apple App Attest) to verify requests originate from a genuine, unmodified app binary
- CORS policy locked down to the org's own domains — reject requests from unknown origins
- Rate limiting per user and per device to protect against credential stuffing, enumeration, and scraping
- No public developer portal or externally published spec — API is not advertised; endpoints are not discoverable via robots.txt or public documentation
- Still requires WAF and DDoS protection — public IP exposure means public threat surface
- Versioning tied to app release cycle — coordinate API changes with app deployments; blue/green versioning reduces the need for long deprecation windows since the org controls the rollout
- Treat the API as internet-facing for security reviews — input validation, output encoding, and injection prevention apply in full

---

### Partner / Enterprise APIs
APIs exposed externally but restricted to a known, vetted set of B2B consumers — enterprise customers, technology partners, or system integrators operating under a signed commercial or data-sharing agreement.

**Key distinction from Public:** Access is provisioned, not self-serve. The consumer is known and accountable. The API can carry richer data and higher-trust operations than a public API, but must not expose data across tenant boundaries.

**Design considerations:**
- Full API-first workflow required — contract reviewed with partners before implementation
- Access restricted at the gateway: OAuth 2.0 client credentials flow with tenant-scoped tokens; optionally enforce IP allowlisting for high-sensitivity integrations
- Scopes and claims encode which partner can access which tenants and operations — validate on every request
- Versioning commitment governed by commercial contract — typically 60-day minimum deprecation notice; major version changes communicated to affected partners directly
- Dedicated rate limit quotas per partner defined in the commercial agreement; quota overages return `429` with negotiated grace handling
- API spec shared under NDA or via a restricted developer portal — not publicly indexed
- Multi-tenancy guardrails are critical: a partner's token must never return another partner's data; enforce tenant isolation at the query layer, not just at the auth layer
- Audit logging of all partner API calls for compliance and dispute resolution
- PII and sensitive fields masked or excluded unless the partner's data agreement explicitly permits access

---

### Public APIs
APIs open to any developer or end user on the public internet.

**Design considerations:**
- Highest stability commitment — breaking changes are visible to the entire ecosystem and are costly to consumers
- Breaking changes always require a new major version with minimum 90-day deprecation notice; communicate via changelog, email, and developer portal announcements
- OAuth 2.0 with scoped JWT tokens for authenticated endpoints; API keys for unauthenticated developer access
- Strict rate limiting enforced per client with published quota tiers; free, standard, and enterprise tiers
- Full public OpenAPI spec on developer portal with working examples, error scenarios, and SDK samples
- Minimal data exposure — return only what the consumer needs; never leak internal identifiers, infrastructure details, or cross-user data
- PII and sensitive fields excluded from all responses
- All traffic via API gateway: auth enforcement, rate limiting, WAF, DDoS protection, and observability
- Security review required before any new public endpoint ships

---

### Third-Party APIs (Consumed)
External vendor or SaaS APIs that the organization integrates with (e.g., payment processors, data providers, communication platforms).

**Design considerations:**
- Always wrap behind an anti-corruption layer (ACL) — internal code never calls vendor SDKs directly; a thin adapter translates between internal domain models and vendor contracts
- Credentials stored in a vault (HashiCorp Vault, AWS Secrets Manager) — never in source code or environment variables
- Pin to a specific API version; do not use `latest` — monitor vendor changelogs for breaking changes
- Implement circuit breakers and fallbacks — design for vendor unavailability
- Validate all data received from the vendor before using it — never trust external payloads
- Log all outbound calls and responses for audit and debugging — mask sensitive fields
- Assess vendor API stability and SLA before building critical paths on it; prefer vendors with published uptime SLAs

---

## API Design Checklist

| Category | Requirement |
|----------|-------------|
| Contract | OpenAPI spec defined before implementation |
| Naming | Resources are plural nouns; URLs are lowercase with hyphens |
| Methods | HTTP methods match their semantic intent |
| Status Codes | Correct 2xx/4xx/5xx codes used throughout |
| Response | Consistent envelope structure on all endpoints |
| Errors | Machine-readable error codes with human-readable messages |
| Versioning | Version in URL path; breaking changes increment major version |
| Auth | OAuth 2.0 / JWT on all endpoints; mTLS for service-to-service |
| Validation | All inputs validated; field-level errors returned on failure |
| Pagination | All collection endpoints are paginated with documented defaults |
| Idempotency | POST endpoints support `Idempotency-Key` header |
| Rate Limits | Rate limit headers returned on every response |
| Documentation | All endpoints documented with examples and error scenarios |
| Observability | Request IDs on all responses; latency and error metrics emitted |

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Verbs in URLs | `/getOrder`, `/createUser` breaks REST conventions | Use HTTP method + resource noun |
| `200 OK` on error | Consumers cannot detect failures reliably | Use correct 4xx/5xx status codes |
| Unpaginated collections | Returns unbounded data; breaks under load | Paginate all collection endpoints |
| Breaking changes in-place | Silently breaks existing consumers | Version the API before making breaking changes |
| Exposing internal models | Couples API to DB schema; prevents refactoring | Use dedicated API request/response types |
| Missing idempotency | Retries cause duplicate side effects | `Idempotency-Key` on all mutating POSTs |
| Deeply nested URLs | `/a/{id}/b/{id}/c/{id}/d` is unmaintainable | Cap nesting at two levels; use query params |
| Chatty APIs | Too many round-trips for a single operation | Support field selection or composite endpoints |
