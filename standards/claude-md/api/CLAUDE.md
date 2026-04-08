# API Standards

Read `../CLAUDE.md` first. This file extends those principles for all HTTP APIs — internal, partner, and public.

---

## API-First Design

**Write the OpenAPI spec before writing code.** The spec is the contract. Implementation follows the contract, not the other way around.

Workflow:
1. Draft OpenAPI 3.1 spec in `docs/api/openapi.yaml`
2. Review with consumers before implementation
3. Generate server stubs and client SDKs from the spec
4. Implement against the generated interfaces
5. Validate implementation against spec in CI (use `openapi-diff` to detect breaking changes)

No spec, no merge.

---

## REST Resource Design

### URL Structure

URLs identify **resources** (nouns), not actions (verbs).

```
# GOOD — resource-oriented
GET    /api/v1/orders
POST   /api/v1/orders
GET    /api/v1/orders/{orderId}
PUT    /api/v1/orders/{orderId}
DELETE /api/v1/orders/{orderId}

GET    /api/v1/orders/{orderId}/line-items
POST   /api/v1/orders/{orderId}/line-items

# BAD — RPC-style verbs in URLs
POST   /api/v1/createOrder
POST   /api/v1/cancelOrder/{id}
GET    /api/v1/getOrderDetails
```

**URL conventions:**
- Lowercase, hyphen-separated path segments: `/line-items`, not `/lineItems` or `/line_items`.
- Plural resource names: `/orders`, `/customers`, `/products`.
- Nest sub-resources at most **two levels deep**: `/orders/{id}/line-items` is fine; `/orders/{id}/line-items/{itemId}/adjustments/{adjId}` is not — flatten it.
- Use query parameters for filtering, sorting, and pagination — not path segments.

### HTTP Methods

| Method | Semantics | Idempotent | Safe |
|---|---|---|---|
| GET | Read a resource or collection | Yes | Yes |
| POST | Create a resource, or trigger an action | No | No |
| PUT | Replace a resource entirely | Yes | No |
| PATCH | Partial update (JSON Merge Patch or JSON Patch) | Depends | No |
| DELETE | Remove a resource | Yes | No |

For non-CRUD actions that don't fit this model, use a **sub-resource command** pattern:

```
POST /api/v1/orders/{orderId}/confirm
POST /api/v1/orders/{orderId}/cancel
POST /api/v1/payments/{paymentId}/refund
```

This keeps URLs noun-based while expressing intent clearly.

---

## HTTP Status Codes

Use status codes precisely. Do not return `200 OK` with an error body.

| Code | Meaning | When to use |
|---|---|---|
| `200 OK` | Successful GET, PUT, PATCH | Resource returned or updated |
| `201 Created` | Resource created | POST that creates a resource; include `Location` header |
| `202 Accepted` | Async operation accepted | Background job enqueued; return status polling URL |
| `204 No Content` | Successful with no body | DELETE, or PUT/PATCH returning nothing |
| `400 Bad Request` | Malformed request | JSON parse error, required field missing |
| `401 Unauthorized` | Not authenticated | Missing or invalid credentials |
| `403 Forbidden` | Authenticated but not authorized | Valid token, insufficient permissions |
| `404 Not Found` | Resource not found | ID does not exist |
| `409 Conflict` | State conflict | Duplicate creation, optimistic lock failure |
| `422 Unprocessable Entity` | Business validation failure | Valid JSON but fails domain rules |
| `429 Too Many Requests` | Rate limit exceeded | Include `Retry-After` header |
| `500 Internal Server Error` | Unexpected server error | Never return implementation details |
| `502 Bad Gateway` | Upstream service failure | When proxying to a failing upstream |
| `503 Service Unavailable` | Service temporarily down | During maintenance or overload; include `Retry-After` |

Never use `200` with a body field like `"success": false`. Use the appropriate 4xx or 5xx code.

---

## Request and Response Shapes

### Consistent Response Envelope

All collection responses use an envelope. Single resource responses return the resource directly (no wrapping).

**Single resource:**
```json
GET /api/v1/orders/ord-123

{
  "id": "ord-123",
  "customerId": "cust-456",
  "status": "confirmed",
  "total": { "amount": "149.99", "currency": "USD" },
  "createdAt": "2025-03-31T12:00:00Z"
}
```

**Collection with pagination:**
```json
GET /api/v1/orders?pageSize=20&cursor=abc

{
  "data": [ ... ],
  "pagination": {
    "pageSize": 20,
    "nextCursor": "xyz",
    "hasMore": true,
    "totalCount": 450
  }
}
```

**Async / accepted response:**
```json
POST /api/v1/reports/generate  →  202 Accepted

{
  "jobId": "job-789",
  "status": "queued",
  "statusUrl": "/api/v1/jobs/job-789",
  "estimatedCompletionSeconds": 30
}
```

### Timestamps and IDs

- All timestamps in **ISO 8601 UTC** with timezone: `2025-03-31T12:00:00Z`.
- All IDs are **strings**, not integers. Use UUIDs (`uuid4`) or a semantically meaningful prefixed ID (`ord-uuid`, `cust-uuid`). Never expose database auto-increment integers as public identifiers.
- All monetary amounts are **strings with explicit currency**: `{ "amount": "149.99", "currency": "USD" }`. Never use floating-point for money.
- Enumerations are **SCREAMING_SNAKE_CASE strings**: `"PENDING"`, `"CONFIRMED"`, `"CANCELLED"`.

---

## Error Response Shape (RFC 9457 Problem Details)

All error responses conform to [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457). Content-Type is `application/problem+json`.

```json
{
  "type": "https://errors.example.com/order-validation-failed",
  "title": "Order Validation Failed",
  "status": 422,
  "detail": "The order could not be created because one or more fields failed validation.",
  "instance": "/api/v1/orders",
  "correlationId": "req-abc-123",
  "timestamp": "2025-03-31T12:00:00Z",
  "errors": [
    {
      "field": "items[0].quantity",
      "code": "MUST_BE_POSITIVE",
      "message": "Quantity must be greater than zero"
    }
  ]
}
```

Rules:
- `type` is a URI (stable URL documenting the error; can 404, but must be stable).
- `title` is human-readable and **does not change** for the same error type.
- `detail` is specific to this occurrence and may vary.
- `correlationId` links to distributed traces. Always include it.
- `errors` array contains field-level validation errors when `status` is 422.
- **Never include** stack traces, SQL errors, or internal service names in error responses.

---

## API Versioning

### Strategy

Use **URL path versioning**: `/api/v1/`, `/api/v2/`.

- Version on **breaking changes only**: removing fields, changing field types, changing status codes, renaming resources.
- Adding new optional fields is not a breaking change.
- Never remove a version without a deprecation period of at least **6 months** and documented migration guide.

```
# Current
GET /api/v1/orders

# After breaking change (v1 kept for deprecation period)
GET /api/v2/orders
```

### Deprecation

When deprecating a version:
1. Add `Deprecation: true` and `Sunset: <date>` response headers.
2. Log warnings when deprecated endpoints are called.
3. Communicate via API changelog and notify consumers directly.
4. Remove only after all consumers have migrated (verified via access logs).

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 31 Dec 2025 00:00:00 GMT
Link: <https://api.example.com/api/v2/orders>; rel="successor-version"
```

---

## Authentication and Authorization

### Authentication Patterns

| API Tier | Authentication Method |
|---|---|
| Internal service-to-service | mTLS + short-lived JWT (SPIFFE/SPIRE or Workload Identity) |
| BFF / first-party clients | OAuth 2.0 Authorization Code + PKCE → JWT access token |
| Partner APIs | OAuth 2.0 Client Credentials → JWT access token |
| Public APIs | API Key (in `Authorization: ApiKey <key>` header) + optional OAuth |

**Never accept credentials in URL query parameters.** They appear in logs, browser history, and proxy access logs.

### JWT Validation

Every service validates JWTs independently. Never pass raw tokens to downstream services. Each service validates:
- Signature (against JWKS endpoint)
- `iss` (issuer)
- `aud` (audience matches this service)
- `exp` (not expired)
- `nbf` (not before)

### Authorization

Use **OAuth 2.0 scopes** for coarse-grained access and **claims-based policies** for fine-grained:

```
# Scope-based (coarse)
scope: orders:read orders:write

# Claims-based (fine-grained — checked in business logic)
sub: user-123
tenantId: tenant-456
roles: ["orders-manager"]
```

Return `403 Forbidden` (not `404 Not Found`) when a resource exists but the caller lacks permission. Returning `404` to mask existence is only appropriate for especially sensitive resources (e.g. admin APIs).

---

## Pagination

**Cursor-based pagination** is the default for large or frequently updated collections.

```
# Request
GET /api/v1/orders?pageSize=20&cursor=eyJpZCI6ImFiYyJ9

# Response
{
  "data": [...],
  "pagination": {
    "nextCursor": "eyJpZCI6InhjeiJ9",
    "hasMore": true
  }
}
```

Use **offset-based pagination** only for small, stable collections where the consumer needs to jump to an arbitrary page (e.g. admin UIs).

Rules:
- Default `pageSize` is 20. Maximum `pageSize` is 100 (never return unbounded lists).
- Cursors are opaque base64-encoded tokens. Consumers must not parse or construct them.
- `totalCount` is included only when it can be computed cheaply (avoid `COUNT(*)` on large tables).

### Filtering and Sorting

```
GET /api/v1/orders?status=CONFIRMED&customerId=cust-456
GET /api/v1/orders?sort=createdAt:desc,total:asc
GET /api/v1/orders?fields=id,status,total   # sparse fieldsets
```

- Filtering: query parameters named after the field.
- Sorting: `sort=field:direction` with comma-separated pairs.
- Sparse fieldsets: `fields=` to reduce payload size.
- Do not expose direct database column names as filter keys — use domain-aligned names.

---

## Idempotency

All **mutating operations** that are retried by clients must be idempotent.

```http
POST /api/v1/orders
Idempotency-Key: client-generated-uuid-v4

{ ... }
```

Rules:
- The server stores the response for the idempotency key for at least 24 hours.
- If the same key is received again with the same payload, return the stored response.
- If the same key is received with a different payload, return `422` with an error explaining the conflict.
- Generate keys client-side (UUID v4). Never generate server-side idempotency keys.

---

## Rate Limiting

Every API endpoint is rate-limited. Limits are documented in the OpenAPI spec.

### Response Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 423
X-RateLimit-Reset: 1743422400
```

When a limit is exceeded:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1743422400
```

### Limits by Tier

| API Tier | Default Rate Limit |
|---|---|
| Internal | 10,000 req/min per service identity |
| First-party / BFF | 1,000 req/min per client |
| Partner | 500 req/min per API key |
| Public (unauthenticated) | 60 req/min per IP |

Apply rate limits per **authenticated identity** (not per IP for authenticated callers — IPs change with NAT/proxies).

---

## OpenAPI / Swagger Standards

The spec is the source of truth. Every endpoint must be fully documented.

```yaml
# openapi.yaml — required fields per endpoint
paths:
  /api/v1/orders:
    post:
      operationId: createOrder        # camelCase, unique across the spec
      summary: Create a new order     # one sentence
      description: |                  # full description with business rules
        Creates a new order in PENDING status. The order will not be confirmed
        until payment is processed via the /confirm endpoint.
      tags: [Orders]
      security:
        - BearerAuth: [orders:write]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateOrderRequest'
            examples:
              minimal:
                $ref: '#/components/examples/CreateOrderMinimal'
      responses:
        '201':
          description: Order created successfully
          headers:
            Location:
              schema: { type: string }
              description: URL of the created order
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Order'
        '422':
          $ref: '#/components/responses/ValidationError'
        '429':
          $ref: '#/components/responses/RateLimitExceeded'
```

Rules:
- Every endpoint has `operationId`, `summary`, `tags`, and `security`.
- Every response code is documented, including `4xx` and `5xx`.
- Every schema property has `description` and appropriate constraints (`minimum`, `maxLength`, `pattern`).
- Include at least one example per request body.
- Breaking changes detected by `openapi-diff` in CI fail the build until explicitly acknowledged.

---

## Asynchronous APIs

For operations that take longer than ~500ms, use an async pattern:

```
POST /api/v1/reports          →  202 Accepted  { "jobId": "...", "statusUrl": "..." }
GET  /api/v1/jobs/{jobId}     →  200 { "status": "RUNNING", "progressPercent": 45 }
GET  /api/v1/jobs/{jobId}     →  200 { "status": "COMPLETED", "resultUrl": "..." }
GET  /api/v1/reports/{id}     →  200 { result }
```

- Never make the client poll more frequently than every 2 seconds.
- Support webhooks as an alternative to polling for partner/enterprise consumers.
- Jobs expire after a defined TTL (document this in the spec).

---

## Security Standards

- **Input validation**: Validate all request inputs at the API layer. Do not pass unvalidated input to the domain.
- **Output encoding**: JSON serialization handles most cases, but be explicit about not rendering HTML from user-supplied data.
- **CORS**: Allowlist specific origins. Never use wildcard `*` for authenticated APIs.
- **Security headers**: Include on all responses:

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'
Cache-Control: no-store   (for authenticated responses)
```

- **Sensitive data in URLs**: Never put tokens, passwords, or PII in URL paths or query strings. They appear in logs and browser history.
- **Mass assignment**: Explicitly allowlist which request fields are bound to domain objects. Never bind entire request bodies to domain entities.

---

## API Changelog

Maintain a `CHANGELOG.md` for the API:

```markdown
## [2.3.0] — 2025-03-31
### Added
- `GET /api/v2/orders` now supports `currency` filter parameter
### Deprecated
- `GET /api/v1/orders` — sunset date 2025-12-31, migrate to v2

## [2.2.0] — 2025-02-15
### Fixed
- `total.amount` now correctly returns string (was number — breaking fix from 2.1.0)
```

---

## Related Standards

- `../CLAUDE.md` — Root engineering principles
- `../backend/java/CLAUDE.md` — Java controller implementation
- `../backend/dotnet/CLAUDE.md` — ASP.NET Core endpoint implementation
- `standards/detailed/api-design.md` — Detailed API design principles and taxonomy
