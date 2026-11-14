# Phase 1 domain and storage contract

Use `storage.database.connect(path)` and `core.service.Service(connection, owner_uuid)`.
The caller owns and closes the connection; use one connection per thread. Owner scope
is a local data boundary, not authentication. Phase 6 supplies authenticated identity.
Create/update/delete return records; update/delete require `expected_version`.
`get` and `list` hide tombstones unless explicitly requested. `pending` is owner-scoped
and ordered by durable insertion sequence. No API credentials or network are needed.

All five entity schemas are defined in core/models.py. Domain dates use YYYY-MM-DD;
metadata timestamps use UTC ISO 8601. Required text is nonblank and at most 200
characters, notes/descriptions allow 10,000, URLs 2,048. Collections allow 100 text
entries. Unknown fields, unsafe URL schemes, URL credentials, invalid dates/enums
and reversed date ranges are rejected. Project slugs are lowercase hyphenated ASCII.
Live project slugs and case-insensitive skill names are unique per owner. Optional
fields may be absent or null except collections. Status and proficiency vocabularies
are explicit in ENUMS; CLI/API must reuse them rather than introduce new rules.

Schema 1 uses a shared records table with a validated JSON payload, indexed owner
and kind, constrained metadata, and partial unique indexes. This keeps shared CRUD
and atomic outbox behavior consistent across all five schemas. Migration SQL ships
inside the client package. Initialization and schema version update run in one
transaction; unknown future schemas and corrupt files fail without replacement.
There is no destructive downgrade; restore a separate backup for rollback. Further
migrations must preserve data and advance user_version transactionally.

Local version increments on every mutation. last_server_version remains zero until
Phase 7; outbox base_version records the last acknowledged server revision, not the
local revision. Phase 7 must serialize/rebase successive pending edits after server
acknowledgments and handle conflicts; this queue must not yet be transmitted.
Each queued payload is a snapshot with persistent operation and device UUIDs.
WAL and synchronous FULL protect committed writes; tests cover reopening, an abrupt
process exit before commit, and forced outbox insertion failure. These are not a
claim of hardware power-loss testing.

`export_backup(service, path)` atomically replaces the destination with UTF-8 JSON.
Exports contain private domain records and tombstones, but no credentials or queue
secrets. SHA-256 detects corruption, not malicious tampering or authenticity. Keep
backups in protected storage; encryption/retention tooling belongs to Phase 8.
`import_backup(service, path, dry_run=True)` validates owner, checksum, schema and
records, reporting additions, changes, conflicts, invalid and unchanged counts.
Changed existing records are conflicts and block the entire import; no automatic
merge occurs. Invalid envelopes raise ValidationError. SQLite uniqueness collisions
raise IntegrityError and roll back the entire import, including during dry-run.
Restore into a separate database with the same owner UUID. Restored records retain
IDs/timestamps/local versions but become pending with server revision zero, and
receive new local outbox operations. Cross-device reconciliation is not implemented.

Current executed verification is Windows only: 32 tests, Ruff, mypy, dependency/lock
checks, isolated sdist/wheel build and extracted-wheel smoke pass. Windows/Ubuntu
Phase 1 CI is prepared but not yet executed. CLI, GUI, network sync and encrypted
backup workflows are not present. Exports use a single SQLite read snapshot across
all five categories. Revision arguments must be actual integers matching the loaded
record, and the transactional SQL update checks that revision again.
