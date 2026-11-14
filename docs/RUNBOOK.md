# Runbook status

Phase 1 local domain/SQLite is verified; see DOMAIN_STORAGE.md for migration and
backup usage. There is no CLI, server, installer or deployment to run.
Use README for target development checks and PROGRESS for actual evidence.

Before production delivery, document and verify: Windows/Kali installation; MySQL test
database and least-privilege TLS access; Alembic upgrade/rollback; HTTPS deployment;
encrypted backups and separate-database restore; keyring recovery; corrupt SQLite
diagnostics; outbox retry/conflict resolution; cursor expiry/rebootstrap; service rollback.
Do not run speculative deployment commands or request credentials before Phase 10.
