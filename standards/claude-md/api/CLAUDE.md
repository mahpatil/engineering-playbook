# API Standards

Extends ../CLAUDE.md.

Applies to all HTTP APIs (internal, partner, public). Error body shape, `correlationId` and health endpoints are defined in the root.

## Contract first
- Write `docs/api/openapi.yaml` (OpenAPI 3.1) before code; generate stubs and clients from it. No spec, no merge.
- CI runs `oasdiff breaking` against `main`; a breaking change fails the build unless the version is bumped (enforced by CI).
- Spec lint (Spectral, `spectral:oas` plus the rules below) is enforced in CI:
  - Every operation has a unique camelCase `operationId`, `summary`, `tags` and `security`.
  - Every documented response includes 4xx/5xx via shared `$ref` components; at least one request example.
  - Every schema property has `description` and constraints (`maxLength`, `minimum`, `pattern`).
  
## Status codes (canonical; other files point here)
Never return `200` with an error body.

| Code | Use |
|---|---|
| 200 | GET, or PUT/PATCH returning the resource |
| 201 | Created; include `Location` |
| 202 | Async accepted; return `statusUrl` |
| 204 | No body (DELETE, PUT/PATCH) |
| 400 | Malformed request: unparseable JSON, wrong types, bad query syntax |
| 401 | Missing or invalid credentials |
| 403 | Authenticated, not permitted (use 404 only for admin or sensitive resources) |
| 404 | Resource does not exist |
| 405 / 415 | Method not allowed / unsupported media type |
| 409 | State conflict or business-rule violation: duplicates, illegal state transition, optimistic-lock failure |
| 412 / 428 | `If-Match` ETag mismatch / required precondition header missing |
| 422 | Validation failure: well-formed JSON failing schema or field rules (include `errors[]`); idempotency key reused with a different payload |
| 429 | Rate limited; include `Retry-After` |
| 500 | Unexpected error; no internals |
| 502 / 504 | Upstream failure / upstream timeout |
| 503 | Overload or maintenance; include `Retry-After` |

## URLs and methods
- Nouns, plural, lowercase, hyphenated: `/api/v1/orders/{orderId}/line-items`. Max two nesting levels; flatten deeper.
- Filters, sort and pagination go in query parameters, never path segments.
- Non-CRUD actions are sub-resource commands: `POST /orders/{id}/cancel`. No verbs elsewhere.
- PUT replaces; PATCH uses JSON Merge Patch (`application/merge-patch+json`) unless the spec says JSON Patch. DELETE is idempotent.
- Never accept credentials in query strings.

## Payloads
- Single resource returned bare; collections wrapped as `{ "data": [...], "pagination": {...} }`.
- Timestamps ISO 8601 UTC (`2026-03-31T12:00:00Z`). IDs are opaque strings (UUID or prefixed UUID), never auto-increment integers.
- Money is `{ "amount": "149.99", "currency": "USD" }` with a string amount (ISO 4217 currency); never floats.
- Enums are `SCREAMING_SNAKE_CASE` strings. Bind request fields via explicit allowlist DTOs (no mass assignment).

## Pagination, filtering, sorting
- Cursor pagination by default: `?pageSize=20&cursor=...`; response `pagination: { nextCursor, hasMore }`. Cursors are opaque; clients must not parse them.
- Offset pagination only for small, stable collections (admin UIs).
- Default `pageSize` 20, max 100; never return unbounded lists. Include `totalCount` only when it is cheap.
- Filter: `?status=CONFIRMED`. Sort: `?sort=createdAt:desc,total:asc`. Sparse fields: `?fields=id,status`. Use domain names, not column names.

## Versioning
- URL path major version: `/api/v1/`. Bump only for breaking changes (removed or retyped fields, changed status codes, renamed resources). Adding optional fields is not breaking.
- Deprecation: minimum 6 months, with migration guide. Send `Deprecation: @<unix-timestamp>` (RFC 9745), `Sunset: <HTTP-date>` (RFC 8594) and `Link: <...>; rel="successor-version"`. Remove only when access logs show zero consumers.
- Keep an API `CHANGELOG.md`.

## Idempotency
- Clients send `Idempotency-Key` (UUID v4) on retried POST and PATCH; servers never generate keys.
- Server stores the response for at least 24 h. Same key and payload returns the stored response. Same key with a different payload returns 422.
- Concurrent in-flight request with the same key returns 409.

## Rate limiting
- Every endpoint is limited per authenticated identity (per IP only for unauthenticated callers).
- Send `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset` (IETF draft; `X-RateLimit-*` aliases tolerated) on every response, plus `Retry-After` on 429.

- Defaults (req/min): internal 10,000 per service identity; first-party 1,000 per client; partner 500 per key; unauthenticated 60 per IP.

## Auth specifics
- Tier methods: internal mTLS + short-lived JWT; first-party OAuth Authorization Code + PKCE; partner Client Credentials; public API key header.
- Each service validates JWT signature, `iss`, `aud`, `exp`, `nbf` itself; never forward raw tokens. Scopes (`orders:read`) for coarse access, claims for fine-grained.
- CORS: explicit origin allowlist, never `*` when authenticated.

## Async operations
- Anything over ~500 ms: `POST` returns `202` with `{ jobId, status, statusUrl }`; `GET /jobs/{jobId}` reports `QUEUED | RUNNING | COMPLETED | FAILED` and `resultUrl`.
- Clients poll no faster than every 2 s; offer webhooks to partners. Jobs have a documented TTL.
