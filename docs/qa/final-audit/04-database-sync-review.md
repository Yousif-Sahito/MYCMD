# 4. Database and Distributed Systems Review

## Scope

The pass reviewed SQLite schema/storage, MySQL models/migrations, sync push/pull,
operation idempotency, conflict state and backup code.

## Verified strengths

- Local writes preserve owner scope and optimistic revisions.
- SQLite outbox entries and records commit in one transaction.
- Operation IDs and duplicate replay semantics are persisted.
- Pull uses owner-scoped ordered change logs and cursors.
- Local stale `in_flight` operations recover back to pending.
- Conflict records preserve local/server JSON and resolution state.
- Tombstones are represented in local and server synchronization models.
- Alembic migrations 001 and 002 define the API/sync schema.

## Limitations

The full local Python suite skipped all five real-MySQL tests because
`MYCMD_MYSQL_TEST_URL` was not configured. MySQL behavior is instead covered by
exact-SHA GitHub Actions MySQL jobs.

No real public production MySQL backup/restore or rollback rehearsal was
executed locally.

## Findings

| ID | Severity | Finding | Evidence | Recommendation |
| --- | --- | --- | --- | --- |
| DB-1 | MEDIUM | Real disposable MySQL backup/restore rehearsal remains external | No live disposable infrastructure in this workspace | Run backup/restore and downgrade/upgrade in a disposable CI database |
| DB-2 | LOW | Migration rehearsal script currently requires an explicitly configured separate URL | `scripts/migration_rehearsal.py` | Enforce and document database-name isolation |
| DB-3 | LOW | Hardware power-loss durability is not claimed | Existing storage documentation | Keep simulation coverage separate from hardware evidence |
