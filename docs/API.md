# Phase 6 API

Implement blueprint section 11: `/api/v1/auth/{login,refresh,logout}`, `/api/v1/me`,
collection/detail CRUD for projects, skills, education, certificates and milestones,
`/api/v1/sync/push`, `/api/v1/sync/pull?cursor=...&limit=100`, `/health`, and
`/api/v1/public/portfolio`. There will be no remote shell endpoint.

Use stable pagination and OpenAPI schemas. Errors contain code, message, field errors
and request_id; 400/401/403/404/409/422/429/500 follow the blueprint.
Non-owned records return 404. Sync commits mutation, operation result and change log
atomically; duplicate operations return the original stored result.

Phase 6 implements authentication, private owner-scoped CRUD and the curated public
portfolio endpoint. The `/api/v1/sync/push` and `/api/v1/sync/pull` endpoints are
not implemented in Phase 6 and must not be reported as synchronization functionality.

## Authentication

- `POST /api/v1/auth/bootstrap`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/me`

Refresh credentials are represented by opaque rotated session values and stored only
as SHA-256 verifiable hashes. Access tokens are short-lived signed JWTs.

## Private CRUD

Each of projects, skills, education, certificates and milestones provides:

- `GET /api/v1/{entity}`
- `POST /api/v1/{entity}`
- `GET /api/v1/{entity}/{id}`
- `PATCH /api/v1/{entity}/{id}`
- `DELETE /api/v1/{entity}/{id}`

Create and update payloads use Pydantic validation plus the shared MYCMD domain
validator. Updates use `expected_version` and stale revisions return 409.
