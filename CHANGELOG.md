# Changelog

All notable repository milestones are documented against exact source and CI evidence.
This file does not claim a live public release.

## Unreleased

- Production deployment assets for FastAPI, MySQL and Caddy.
- Encrypted logical MySQL backup/restore helpers.
- Exact-SHA Windows and Ubuntu CI packaging verification.
- Final architecture and engineering documentation.

## Phase 10 - deployment preparation

- Added production settings validation requiring MySQL and HTTPS public origins.
- Added Docker API image, production Compose stack and Caddy static/API routing.
- Added migration and backup rehearsal scripts.
- Exact-SHA CI verified MySQL, Windows, Ubuntu and portfolio jobs.

## Phase 9 - packaging

- Added PyInstaller GUI entry point and executable spec.
- Added Windows and Ubuntu packaged GUI build stages.
- Added clean installed GUI packaging artifacts to CI.

## Phase 8 - hardening

- Added SQLite snapshot verification and encrypted backup/restore.
- Added restore-failure, performance and CLI recovery coverage.
- Upgraded dependency audit findings.

## Phase 7 - synchronization

- Added authenticated push/pull, operation idempotency and ordered cursors.
- Added durable local conflicts and retry recovery.
- Added CLI and GUI conflict resolution surfaces.

## Phase 6 - API and MySQL

- Added FastAPI auth, owner-scoped CRUD and public portfolio serialization.
- Added Alembic migrations and real MySQL CI coverage.

## Phase 5 - public portfolio

- Added React/TypeScript portfolio and allowlisted browser terminal.
- Added Vitest and Playwright coverage.

## Phase 4 - desktop GUI

- Added PySide6 navigation, forms, dashboard, settings and terminal UI.
- Added local Qt WebEngine terminal bridge.

## Phase 3 - real terminal engine

- Added ConPTY/PyWinpty and POSIX PTY session implementations.
- Added real-shell streaming, resize, interrupt and lifecycle tests.

## Phase 2 - native CLI

- Added Typer/Rich CLI, entity CRUD, search, status and sync surfaces.

## Phase 1 - domain and SQLite

- Added shared validation, five entity schemas, migrations, outbox and backups.

## Phase 0 - foundation

- Added Python packaging, lockfiles, Ruff, mypy, pytest and CI structure.
