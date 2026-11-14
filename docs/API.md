# API plan (Phase 6; not implemented)

Implement blueprint section 11: `/api/v1/auth/{login,refresh,logout}`, `/api/v1/me`,
collection/detail CRUD for projects, skills, education, certificates and milestones,
`/api/v1/sync/push`, `/api/v1/sync/pull?cursor=...&limit=100`, `/health`, and
`/api/v1/public/portfolio`. There will be no remote shell endpoint.

Use stable pagination and OpenAPI schemas. Errors contain code, message, field errors
and request_id; 400/401/403/404/409/422/429/500 follow the blueprint.
Non-owned records return 404. Sync commits mutation, operation result and change log
atomically; duplicate operations return the original stored result.
