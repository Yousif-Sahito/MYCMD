# Runbook status

Phase 1 local domain/SQLite is verified; see DOMAIN_STORAGE.md for migration and
backup usage. There is no CLI, server, installer or deployment to run.
Use README for target development checks and PROGRESS for actual evidence.

Before production delivery, document and verify: Windows/Kali installation; MySQL test
database and least-privilege TLS access; Alembic upgrade/rollback; HTTPS deployment;
encrypted backups and separate-database restore; keyring recovery; corrupt SQLite
diagnostics; outbox retry/conflict resolution; cursor expiry/rebootstrap; service rollback.
Do not run speculative deployment commands or request credentials before Phase 10.

## Phase 6 local API

Development MySQL can be started with Docker Compose only where Docker is
installed:

```powershell
docker compose up -d mysql
$env:DATABASE_URL="mysql+pymysql://mycmd:mycmd-test-only@127.0.0.1:3307/mycmd_test"
$env:MYCMD_SECRET_KEY="replace-with-a-random-secret-at-least-32-characters"
$env:MYCMD_BOOTSTRAP_TOKEN="replace-with-a-random-bootstrap-token"
$env:MYCMD_PUBLIC_ORIGIN="http://127.0.0.1:5173"
uv run --extra server alembic upgrade head
uv run --extra server uvicorn server.app.main:app --host 127.0.0.1 --port 8000
```

Docker and MySQL are not required for CLI, SQLite desktop or public portfolio
operation. The API refuses wildcard origins and requires a strong signing key,
database URL and bootstrap token in production configuration.

## Phase 10 production rehearsal

Production deployment assets are:

- `Dockerfile.api` for the FastAPI container
- `compose.production.yaml` for isolated MySQL, API and Caddy static/API routing
- `Caddyfile` for public HTTPS termination and static portfolio serving
- `scripts/mysql_backup.py` for encrypted logical MySQL backup/restore
- `scripts/migration_rehearsal.py` for disposable rollback/forward migrations

Build the portfolio and validate it before starting the stack:

```powershell
cd apps/portfolio
npm ci
npm run build
cd ../..
$env:MYCMD_PUBLIC_DOMAIN="portfolio.example.test"
$env:MYCMD_PUBLIC_ORIGIN="https://portfolio.example.test"
$env:DATABASE_URL="mysql+pymysql://mycmd:replace@mysql:3306/mycmd"
$env:MYCMD_SECRET_KEY="replace-with-a-random-secret-at-least-32-characters"
$env:MYCMD_BOOTSTRAP_TOKEN="replace-with-a-random-bootstrap-token"
python scripts/deployment_check.py
docker compose -f compose.production.yaml up -d --build
```

Do not commit real domains, passwords or certificates. Caddy requires reachable
DNS and ACME access for public HTTPS; a local-only run can validate configuration
but is not production HTTPS evidence.

MySQL backups are encrypted by default through
`MYCMD_MYSQL_BACKUP_PASSWORD`; use `--unencrypted` only for explicitly approved
rehearsal. Restore requires `--confirm` and does not reduce key or checksum checks.

MySQL migration rehearsal requires a separate URL:

```powershell
$env:MYCMD_REHEARSAL_DATABASE_URL="mysql+pymysql://.../mycmd_rehearsal"
python scripts/migration_rehearsal.py --confirm
```
