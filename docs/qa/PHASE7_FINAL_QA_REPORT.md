# MYCMD 2.0 - Phase 7 verification report

STATUS: BLOCKED

Phase 7 source implementation is present, but final release verification is blocked
pending real MySQL and exact-SHA CI evidence.

## Implemented and verified locally

- SQLite schema 2 adds cursor/status and durable conflict storage.
- The server has authenticated `/api/v1/sync/push` and `/api/v1/sync/pull` endpoints.
- Push stores owner-scoped operation responses and change-log entries transactionally.
- Duplicate operation IDs return the original stored response.
- Pull returns owner-scoped ordered pages and the final sequence cursor.
- Bootstrap provisioning is provisioned under a database-backed singleton state.
- The local coordinator recovers stale in-flight operations and persists retry/conflict state.
- CLI and GUI Sync surfaces are implemented.
- Manual keep-server, keep-local, and manual-merge resolution logic is implemented.
- Manual merge validates shared domain rules before queueing a version-checked update.
- A real-MySQL Phase 7 test module now covers push, duplicate replay, stale conflict,
  pull and tombstone scenarios when `MYCMD_MYSQL_TEST_URL` is configured.
- 60 non-GUI unit/integration tests passed.
- 18 SQLite storage tests passed.
- 7 server integration tests passed.
- Ruff and strict mypy passed.
- Navigation and real GUI terminal paste tests passed on repeat.

## Blocked or unverified

- Real MySQL push/pull, concurrent duplicate, and two-device tests require a disposable
  `MYCMD_MYSQL_TEST_URL`.
- Docker/MySQL CLI availability was not confirmed locally; no disposable MySQL URL
  is configured in this environment.
- Kali-specific GUI/terminal verification was not performed.
- Windows and Ubuntu GitHub Actions exact-SHA verification is pending.
- The MySQL tests skip locally and remain pending for exact-SHA Ubuntu/Windows CI.
