# API Contracts

> Baseline for designing new HTTP APIs. Examples are illustrative contracts, not implemented Hex-Kit endpoints.

## 1. Scope and Design Decisions

Read this document before adding or changing an endpoint, request schema, response schema, or externally visible error. The backend guidelines currently contain no implemented API conventions; the defaults below establish a design baseline. Existing published contracts take precedence until an explicit migration is agreed.

The references at the end inform this baseline; their Azure-specific requirements are not automatically project requirements. In particular:

- Use resource-oriented HTTP APIs without introducing Azure headers, OData, mandatory hypermedia, or a new framework solely to match a reference.
- Return `200` with an empty collection for a successful list with no matches.
- Default DELETE to `204` even when the resource is already absent, after authorization. Idempotency concerns effects, not identical responses.
- Reserve `202` for accepted but unfinished work; an already-existing resource alone does not justify it.
- POST and PATCH are not inherently idempotent. Specify retry behavior when an operation has side effects.

These are local choices, not a claim that all references prescribe the same behavior. Record material exceptions and their rationale in the feature contract; use an ADR for architectural decisions. Do not retrofit unrelated endpoints as part of a feature.

## 2. Signatures and Resource Modeling

Use plural resource nouns, lowercase kebab-case path segments, and camelCase JSON fields and query parameters. Keep paths shallow and model business resources rather than database tables. Follow the service's established prefix; `/api` below is illustrative, not a versioning decision.

| Signature | Meaning | Successful synchronous response |
| --- | --- | --- |
| `GET /api/widgets` | List visible widgets | `200` with collection body |
| `GET /api/widgets/{widgetId}` | Read one visible widget | `200` with resource body |
| `POST /api/widgets` | Create a server-identified widget | `201` with resource body and `Location` |
| `PUT /api/widgets/{widgetId}` | Replace the writable representation | `200` with resource body |
| `PATCH /api/widgets/{widgetId}` | Apply a documented partial update | `200` with resource body |
| `DELETE /api/widgets/{widgetId}` | Ensure the widget is absent | `204`, no body |

Implement only required operations. PUT/PATCH do not create missing resources by default. If client-selected IDs and upsert are required, specify that explicitly, including `201` on creation. Define PUT omission behavior for every writable field; do not use PUT for an undocumented partial update.

GET and HEAD must not initiate business mutations. Put filters in query parameters, not pseudo-resource paths such as `/widgets/active`. For domain commands that cannot naturally be modeled as resources, document a POST action and its effects instead of forcing CRUD semantics. Do not invent a generic action framework for one command.

## 3. Request and Response Contracts

### Boundary ownership

- Controller: decode and validate protocol input, authenticate through the established mechanism, map request DTOs to application inputs, and map results/errors to HTTP.
- Application: orchestrate authorization, use cases, transaction boundaries, and atomic effects.
- Domain: enforce business invariants without depending on HTTP status codes or transport DTOs.
- Infrastructure: implement persistence and external integrations behind the project's explicit boundaries.

Never serialize persistence records or mutable domain objects directly. Explicitly select response fields and independently map across boundaries. Enforce resource-level authorization for reads and writes; do not trust a client-supplied owner or tenant identifier. Introduce tenant scoping only when the actual product requires it.

### Schema rules

Document path, query, header, and body inputs: type, requiredness, nullability, length/range, allowed values, defaults, and read-only fields. Reject unknown write fields and unsupported query parameters with `400`; do not silently accept misspelled inputs or mass-assign a request object.

Use `application/json` for ordinary JSON bodies. Specify the accepted PATCH media type and semantics. For `application/merge-patch+json`, omission leaves a field unchanged and `null` removes it; do not interpret `null` as an ordinary assigned value. Choose another documented format when explicit null values are needed.

Represent identifiers as opaque strings. Emit timestamps as UTC RFC 3339 strings. Document units and precision for numeric quantities; use decimal strings or documented minor units for exact money values, and strings for integers outside interoperable JSON numeric precision. Do not silently coerce strings, booleans, and numbers into one another.

### Illustrative create contract

`POST /api/widgets` accepts exactly one writable field: `name`, a required string of 1–100 characters after trimming. A whitespace-only value is invalid. The response contains `id` (opaque string), normalized `name`, and `createdAt` (UTC timestamp); all are required and non-null. The server-owned fields `id` and `createdAt` must not be accepted as write inputs.

```http
POST /api/widgets
Content-Type: application/json

{"name":"Build runner"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json
Location: /api/widgets/w_123

{"id":"w_123","name":"Build runner","createdAt":"2026-09-27T08:00:00Z"}
```

Return a single resource directly. Do not wrap every response in `success`, `status`, or a duplicate HTTP status field. Collections use a stable object shape so pagination metadata does not change the response type.

### Bounded collection example

For an endpoint adopting this offset-based example:

```http
GET /api/widgets?limit=20&offset=0&sort=name
```

```json
{
  "items": [{"id":"w_123","name":"Build runner","createdAt":"2026-09-27T08:00:00Z"}],
  "nextLink": null
}
```

`limit` is an integer from 1–100, default 20; `offset` is a nonnegative integer, default 0. `sort` accepts `name` or `-name`, default `name`, with `id` ascending as a stable tie-breaker. Other values return `400`. `nextLink` is a server-generated relative URL preserving query choices, or `null` at the end. Empty results are `{"items":[],"nextLink":null}`. Do not require an expensive total count without a product need.

Offset pagination can skip or repeat entries during concurrent changes; it is not a snapshot. Use a documented opaque cursor for large or frequently changing collections when necessary. Define invalid/expired cursor behavior and bind cursors to query and authorization scope. Neither cursor possession nor pagination links bypass authorization. Filtering, sorting, and field selection require explicit allowlists; never interpolate client expressions into persistence queries.

### Error body

Use the following JSON shape for application-generated failures. Centralize HTTP mapping at the protocol boundary; do not expose stack traces, SQL, credentials, internal paths, or raw dependency responses.

```json
{
  "error": {
    "code": "InvalidRequest",
    "message": "One or more fields are invalid.",
    "details": [{"code":"InvalidField","target":"name","message":"Provide a non-empty name."}],
    "requestId": "req_123"
  }
}
```

`code`, `message`, and `requestId` are required strings; `details` is an optional array of objects with required string `code`, `target`, and `message`. Codes are stable machine-readable values; messages are human-readable and must not drive client logic. `target` names the public input field without echoing sensitive values. The server controls or validates correlation identifiers and associates them with sanitized diagnostic logs. Infrastructure-generated failures may not have this body; clients must still interpret HTTP status correctly.

## 4. Validation and Error Matrix

Choose stable domain-specific codes where needed; these defaults apply to new contracts.

| Condition | HTTP status / code | Required behavior |
| --- | --- | --- |
| Malformed JSON, invalid field/query, unknown write field | `400 InvalidRequest` | No mutation; identify safe field targets |
| Missing or invalid authentication | `401 Unauthenticated` | Include the applicable `WWW-Authenticate` challenge |
| Authenticated caller lacks permission | `403 Forbidden` | No mutation or protected data |
| Resource missing, or existence must be concealed | `404 NotFound` | Apply a consistent disclosure policy |
| Method unsupported on an existing route | `405 MethodNotAllowed` | Include `Allow` |
| No supported response representation matches `Accept` | `406 NotAcceptable` | Do not return an incompatible representation |
| Uniqueness or current business-state conflict | `409 Conflict` | No partial mutation |
| Stale `If-Match` on a conditional write | `412 PreconditionFailed` | Preserve the current resource |
| Request body exceeds documented limit | `413 PayloadTooLarge` | Reject before unbounded buffering |
| Unsupported request media type | `415 UnsupportedMediaType` | Do not guess the body format |
| Required write precondition omitted | `428 PreconditionRequired` | Only for endpoints requiring conditional writes |
| Rate limit reached | `429 TooManyRequests` | Include `Retry-After` when a retry delay is known |
| Unexpected application failure | `500 InternalError` | Safe message and correlated internal diagnostics |
| Temporary service unavailability | `503 ServiceUnavailable` | Include `Retry-After` when known |

Do not return `200` for an HTTP operation that failed. Validate input before mutations; check authorization before exposing resource state. Business invariant failures belong in Domain and are translated at the boundary. Do not map every dependency failure to a client error.

### Concurrency, retries, and asynchronous work

For resources vulnerable to lost updates, define strong ETags and require `If-Match` on writes. Compare and mutate atomically; a separate read-then-write check is insufficient. Document whether cache validation is supported: a matching `If-None-Match` on GET returns `304` without a body. Specify `Cache-Control` deliberately; use `no-store` for sensitive responses and prevent authenticated data from entering shared caches.

For retryable side-effecting POST operations, document the deduplication mechanism before promising safe retries. If using an idempotency key, define its header, scope (caller and operation), payload comparison, retention period, concurrent-duplicate behavior, and replay result. Persist deduplication and effects atomically where possible; describe recovery for external effects. Reject reuse with different input as `409`. Never claim an unlimited exactly-once guarantee. Bound retry attempts and honor cancellation, backoff, and `Retry-After`.

For long-running work, acknowledge with `202` only after reliable acceptance, with `Location` pointing to an authorized operation-status resource. Define pending/running/succeeded/failed states, result links, safe error details, polling guidance, expiry, and cancellation semantics if supported. A successful status-resource GET may return `200` with a failed job state: retrieving status succeeded even though the background job failed. Do not mark work complete at acceptance time.

### Evolution and documentation

Maintain a machine-readable OpenAPI contract alongside implementation using the project's existing tools. Describe schemas, security, status codes, headers, limits, and examples; do not add tooling solely for this guideline.

Before changing a published contract, identify consumers, including SDKs and integrations. Field removal/rename, type changes, stricter validation, new required inputs, changed status/error semantics, and altered pagination can break clients. Even additive enum values need consumer analysis. Follow an existing versioning scheme; choose and document one when a breaking external change actually requires it, with migration, deprecation, and rollback plans. Do not add internal compatibility shims by default.

## 5. Good, Base, and Bad Cases

- **Good:** A valid create returns the persisted representation and resolvable `Location`; an authorized read retrieves that resource.
- **Base:** A list with no visible matches returns `200`, an empty `items` array, and `nextLink: null`; a completed delete has no response body.
- **Bad:** Invalid `name` returns `400 InvalidRequest` with a safe field target and no write; an unauthorized caller cannot obtain another user's resource through its ID or a pagination link.

## 6. Verification Requirements

For behavior changed by a feature, first run relevant existing tests. Add focused assertions only where those tests do not cover the changed behavior; do not create a framework, broad matrix, or unrelated coverage for this document.

- Verify the exact success status, schema, content type, and required headers.
- Verify invalid input produces the specified error and no side effects.
- Verify changed authorization boundaries and empty collection behavior where applicable.
- If introducing conditional writes or deduplication, verify a stale/concurrent duplicate request cannot overwrite data or repeat effects.
- If introducing asynchronous work, verify acceptance, terminal state, and status-resource authorization.
- Check affected consumers and OpenAPI definitions for compatibility; inspect the final diff for unrelated changes.

## 7. Wrong vs Correct

| Wrong | Correct | Reason |
| --- | --- | --- |
| `GET /api/deleteWidget?id=w_123` | `DELETE /api/widgets/w_123` | Reads must not perform business mutations |
| `200 {"success":false}` | Appropriate `4xx`/`5xx` with the error contract | Clients and intermediaries can trust HTTP semantics |
| Serialize an ORM record | Explicitly construct the response DTO | Storage details and private fields stay behind the boundary |
| Accept arbitrary body keys | Validate a writable-field allowlist | Prevent unintended privileged-field updates |
| Blindly retry POST after a timeout | Use documented deduplication or reconcile the outcome | A timeout does not prove that the write failed |

## References

Reviewed on 2026-09-27. This document adapts the sources to the project's architecture and scope; concrete example schemas, limits, and field names above are local choices.

- [Microsoft REST API Guidelines](https://github.com/Microsoft/api-guidelines) and its [Azure guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md): contract consistency, conditional requests, and retry-aware design. Azure-specific platform policy is not inherited.
- [Microsoft Azure Architecture Center: Web API design](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design): resource modeling, HTTP semantics, pagination, asynchronous operations, and evolution.
- [Florimond Manca: RESTful API Design — 13 Best Practices](https://florimond.dev/en/posts/2018/08/restful-api-design-13-best-practices-to-make-your-users-happy): supplementary usability guidance on readable endpoints and predictable responses, not a protocol authority. Interpret status codes by operation outcome rather than assigning one code to every use of a method.
