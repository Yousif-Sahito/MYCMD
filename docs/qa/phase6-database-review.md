# Phase 6 database review

SQLAlchemy models and migration 001 cover users, refresh sessions and owner-scoped
records. Foreign keys, indexes, email/token uniqueness and version/kind/status checks
are present. Update/delete and refresh-session reads use row locking.

Local SQLite HTTP tests do not establish real-MySQL support. The real-MySQL tests
remain skipped unless `MYCMD_MYSQL_TEST_URL` is supplied. Ubuntu CI adds MySQL 8.4
and Alembic upgrade steps.
