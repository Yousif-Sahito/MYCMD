# Phase 3 terminal engine

The local terminal package has a shared `TerminalSession` and typed
`TerminalBackend` protocol. Windows uses PyWinpty with ConPTY explicitly
selected; POSIX uses `pty.fork`, a controlling terminal, process groups and
window-size ioctls. The session streams bounded byte events and combines stdout
and stderr as native PTYs do. The desktop renderer is deferred to Phase 4. The
local engine has no network listener and is not reused by the public portfolio
terminal.

# Architecture decisions

Source: blueprint sections 1–25. Implementation status is tracked separately.

- Native CLI: Typer/Rich commands call shared Python domain services. The host shell
  retains OS behavior; optional shell mode explicitly launches a native shell.
- Desktop: PySide6 with bundled xterm.js in Qt WebEngine and a trusted local bridge.
  It will consume the Phase 3 session API and maintain its own bounded 5,000-line
  scrollback; the engine owns process I/O and lifecycle, not GUI rendering.
- Public portfolio: React/TypeScript/xterm.js and a deterministic local command registry.
  No shell bridge, WebSocket shell, eval, subprocess access or generic command API.
- Core: validation and services shared by CLI and GUI. UUID/owner/UTC/version/tombstone
  metadata on all five entities; consistent date, enum, length and URL constraints.
- SQLite: WAL, migrations and atomic record + outbox transactions. Local owner scoping,
  persisted operation IDs and per-device cursors. Never silently replace a corrupt DB.
- Server: FastAPI/Pydantic/SQLAlchemy/Alembic and authoritative MySQL 8+.
  Authenticated identity supplies owner scope; client owner IDs cannot authorize access.
- Sync: ordered idempotent pushes, optimistic versions, transactional change log,
  atomic pull page + cursor, durable conflicts, tombstones and bounded retries.
- Secrets: OS keyring on desktop, server secrets outside client distribution, HTTPS only
  remotely. Curated public serialization explicitly excludes private fields.

The client wheel includes only `src/mycmd`; server and portfolio are separate artifacts.
The platform-specific `pywinpty` runtime dependency is locked only on Windows.
Terminal integration tests exercise real commands and persistent shell state on both OSes.
