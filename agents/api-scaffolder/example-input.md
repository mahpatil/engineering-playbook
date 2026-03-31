# Example Input: Scaffold a Payments API in Java

## Request

Scaffold the `PaymentsAPI` with `/payments` and `/refunds` resources using Java Spring Boot and OAuth2 JWT authentication. POST `/payments` must be idempotent.

## Parameters

| Field | Value |
|-------|-------|
| `api_name` | `PaymentsAPI` |
| `resources` | `["payments", "refunds"]` |
| `backend_language` | `java` |
| `auth_type` | `oauth2-jwt` |
| `api_version` | `v1` |
| `base_package` | `com.acme.payments` |
| `idempotent_resources` | `["payments"]` |
| `event_resources` | `["payments"]` |

## Context

### Payments resource
- A `payment` represents a card transaction authorisation.
- Key fields: `id` (UUID), `amount` (decimal), `currency` (ISO 4217, e.g. `GBP`), `status` (`PENDING` \| `AUTHORISED` \| `DECLINED` \| `SETTLED`), `merchantId` (UUID), `createdAt` (ISO 8601), `updatedAt` (ISO 8601).
- `POST /api/v1/payments` — create a new payment authorisation. Requires `Idempotency-Key` header (UUID). Returns 201 with `Location` header.
- `GET /api/v1/payments` — cursor-paginated list, filterable by `status` and `merchantId` query params.
- `GET /api/v1/payments/{paymentId}` — get a single payment.
- `PATCH /api/v1/payments/{paymentId}` — update status only (e.g. merchant-initiated settlement trigger).
- `DELETE /api/v1/payments/{paymentId}` — cancel/void a pending payment.

### Refunds resource
- A `refund` belongs to a payment: `/api/v1/payments/{paymentId}/refunds`.
- Key fields: `id` (UUID), `paymentId` (UUID), `amount` (decimal), `reason` (string), `status` (`PENDING` \| `PROCESSED` \| `FAILED`), `createdAt` (ISO 8601).
- Only `POST` (create refund) and `GET` (list/get) — no update or delete.

### Error cases to model explicitly
- `400` — invalid request body (missing required fields, invalid currency code).
- `404` — payment or refund not found.
- `409` — duplicate `Idempotency-Key` with different request body.
- `422` — business rule violation (e.g. refund amount exceeds original payment amount).
- `429` — rate limit exceeded.

### Security
- All endpoints require a valid JWT in `Authorization: Bearer <token>`.
- Scope `payments:read` required for GET endpoints.
- Scope `payments:write` required for POST/PATCH/DELETE endpoints.

## Expected Output

### `openapi.yaml`
- OpenAPI 3.1, title `PaymentsAPI`, version `1.0.0`.
- BearerAuth security scheme (JWT).
- `payments` and `refunds` paths as described above.
- Cursor pagination on all list endpoints.
- `Idempotency-Key` header on `POST /api/v1/payments`.
- All errors reference `ProblemDetails` component with correct type URIs.
- `CursorMeta` and `ProblemDetails` defined in `components/schemas`.

### `src/controllers/PaymentsController.java`
- `@RestController` at `/api/v1/payments`.
- Methods: `listPayments`, `createPayment`, `getPayment`, `updatePayment`, `cancelPayment`.
- Delegates to `PaymentsService` interface (stub provided).
- `@PreAuthorize("hasAuthority('payments:write')")` on mutating methods.

### `src/controllers/RefundsController.java`
- `@RestController` at `/api/v1/payments/{paymentId}/refunds`.
- Methods: `listRefunds`, `createRefund`, `getRefund`.

### `src/errors/ApiError.java`
- Java record or class implementing RFC 9457 `ProblemDetails` fields.
- `@RestControllerAdvice` `GlobalExceptionHandler` stub with handlers for `ConstraintViolationException`, `MethodArgumentNotValidException`, and a catch-all for `Exception`.

### `docs/VERSIONING.md`
- Current version: v1 (date placeholder).
- Breaking change policy: new major version required for field removal or type change.
- Deprecation: `Deprecation` + `Sunset` headers; 6-month minimum support window.

## What This Should NOT Contain
- Offset/limit pagination parameters.
- Plain string error responses.
- More than two levels of URL nesting.
- `Accept` header versioning.
- Real domain names, email addresses, or account IDs.
