# Blueprint text extracted from the supplied PDF

Source: ../MYCMD_V2_Codex_Implementation_Blueprint.pdf. All 15 page streams extracted; page labels retained. This is a text transcription, not the missing original Markdown. PDF bullet glyphs appear as DEL characters in the extraction. Tables retain reading order rather than layout.

--- PAGE 1 ---
MYCMD 2.0 | Codex Implementation Blueprint
1
MYCMD 2.0
Complete Software Requirements Specification, Terminal Architecture, Portfolio Integration and Codex Execution Contract
Version 2.0 | 14 November 2026 | Implementation-ready engineering blueprint
Supersedes and expands the supplied 11-page MYCMD v1.1 SRS. Preserve its offline-first personal command-centre
requirements while adding an authentic terminal experience.
Executive decision
Build THREE distinct surfaces over shared domain services: (A) real native CLI launched in an existing system shell, (B)
desktop GUI with a real pseudoterminal-backed session, and (C) browser portfolio terminal with a restricted, deterministic
command registry. Do NOT expose a real OS shell to anonymous portfolio visitors.
Authenticity means actual process execution, real stdout/stderr, correct exit status, working directory and signals on trusted
local clients. A browser terminal may look and feel authentic but must clearly distinguish supported portfolio commands from
unsupported OS commands.
Definition of done
The deliverable is a working source repository, not mockups: installed mycmd command; functional desktop terminal; public
portfolio terminal; complete CRUD; offline persistence; authenticated API; tested synchronization; documented packaging
and reproducible automated acceptance tests. Never claim a feature is finished without a passing test or clearly
documented manual verification.
1. Scope and original requirements preserved
 Python CLI (Typer + Rich) with projects, skills, education, certificates, milestones, status, help, import/export and sync.
 Desktop GUI sharing validation and persistence with CLI.
 SQLite local cache and durable pending operations; REST API over HTTPS; MySQL authoritative online store; stable
UUIDs, optimistic versions, idempotency, tombstones and conflicts.
 Kali Linux and Windows as primary targets; macOS only after separate verification.
 Single personal owner account initially; ownership authorization built in for future accounts.
 Authentication, secure token handling, migrations, backups, packaging, diagnostics and recovery.
2. Explicit execution boundaries
Surface
Allowed behavior
Forbidden behavior
Installed mycmd CLI
Native OS shell remains host; mycmd
subcommands manage data. Optional
shell mode launches user-selected
shell.
Pretend to emulate arbitrary OS
commands or require server to execute
them.
Desktop terminal
Spawn a local shell through
PTY/ConPTY with user privileges and
consent.
Run commands as admin/root
automatically; silently execute startup
scripts.
--- PAGE 2 ---
MYCMD 2.0 | Codex Implementation Blueprint
2
Surface
Allowed behavior
Forbidden behavior
Public website
Allowlisted portfolio commands,
navigation, content search, optional
safe read-only API.
Arbitrary shell execution, SQL,
filesystem access, secrets, uploads
that execute code.
--- PAGE 3 ---
MYCMD 2.0 | Codex Implementation Blueprint
3
3. Functional requirements and priority
TR-01 [MUST] — Real local interactive shell with stdout/stderr streaming and exit codes
TR-02 [MUST] — PTY/ConPTY terminal dimensions, resize, cursor, ANSI/VT sequences
TR-03 [MUST] — Windows PowerShell and CMD selection; Linux bash/zsh where installed
TR-04 [MUST] — Keyboard input, Ctrl+C, Ctrl+D, tab completion handled by shell
TR-05 [MUST] — Terminal scrollback, search, copy/paste, selection, clear and themes
TR-06 [MUST] — Safe terminal session start/stop and child process cleanup
TR-07 [MUST] — Portfolio terminal command parser and explicit unsupported-command messages
TR-08 [MUST] — Mobile and screen-reader accessible web fallback
FR-01 [MUST] — Project CRUD: title, description, status, tech, links, dates, notes
FR-02 [MUST] — Skills CRUD: name, category, level, notes, updated date
FR-03 [MUST] — Education CRUD: institution, program, status, dates, notes
FR-04 [MUST] — Certificates CRUD: issuer, URL/ID, dates, notes
FR-05 [MUST] — Milestones CRUD: priority, due date, status, completed date
FR-06 [MUST] — CLI help, status, search, export/import, interactive mode, sync
FR-07 [MUST] — Desktop forms, searchable lists, settings and sync indicators
FR-08 [MUST] — SQLite transactional writes, durable queue and restart persistence
FR-09 [MUST] — Push/pull, idempotency, conflict resolution and tombstones
FR-10 [MUST] — Auth, ownership, backups, diagnostics and tested packaging
4. Recommended technology stack
Layer
Choice / rationale
Python runtime
Python 3.12 or 3.13; lock and test exact supported version
Native CLI
Typer + Rich; prompt_toolkit only for optional MYCMD
interactive command mode
Desktop
PySide6 with QTermWidget only if supported; otherwise
terminal emulator via xterm.js inside Qt WebEngine and
PTY bridge
Local terminal backend
POSIX: pty/fork or pywinpty-compatible library; Windows:
ConPTY via supported maintained wrapper
Browser terminal
React + TypeScript + xterm.js for display/input; no remote
shell endpoint
Local data
SQLite with WAL, migrations, transactions
API
FastAPI, Pydantic, SQLAlchemy, Alembic, Uvicorn
--- PAGE 4 ---
MYCMD 2.0 | Codex Implementation Blueprint
4
Layer
Choice / rationale
Online data
MySQL 8+, isolated DB user, TLS where available
Testing
pytest, httpx, Playwright, Vitest, integration MySQL in
Docker
Build
uv or pip with lockfile, PyInstaller for OS-specific builds
If the selected PTY/ConPTY dependency is incompatible with a target OS/Python version, Codex must investigate and
document a tested replacement before claiming support. Never substitute a fake terminal.
5. Terminal experience specification
 Startup: fast loading, clearly labeled MYCMD title and active shell, current directory, online status and optional welcome
help. Avoid claiming to be Microsoft CMD or a proprietary product.
 Session: persist shell process while window remains open; support cd, pipes, redirection, environment changes and
long-running programs as performed by the real shell.
 Rendering: ANSI colors, cursor movement, Unicode, wrapping, alternate screen, selection, hyperlinks only after validation,
high contrast and scalable fonts.
 Keyboard: enter, arrows, Home/End, Backspace/Delete, Ctrl+C interrupt, Ctrl+L clear when supported, Ctrl+Shift+C/V
copy/paste, IME support.
 Resize: propagate cols/rows to PTY and redraw; preserve bounded scrollback; scroll with keyboard/mouse.
 Lifecycle: exit closes session cleanly, reconnect/restart opens a new session with transparent message, not silently
replaying prior commands.
 Working directory: initial home or explicitly configured folder; never run commands as privileged user by default.
 Errors: show real shell error text and exit code, distinguish application failures from command failures.
--- PAGE 5 ---
MYCMD 2.0 | Codex Implementation Blueprint
5
6. Portfolio web terminal — command contract
Use a local TypeScript registry; parse quoted arguments safely, with deterministic tokenization and clear syntax errors. No
eval, shell interpolation, exec, child_process, or arbitrary server command dispatch. Render command output as text nodes,
never unsafe HTML.
help                     list available commands
about                    profile overview
projects [--status x]    list projects
project <slug>           show project details
skills                   list skill categories
education                education timeline
certificates             verified certificate links
milestones               selected milestones
experience               experience summary
contact                  contact options
resume                   open validated resume URL
github                   open configured GitHub URL
linkedin                 open configured LinkedIn URL
theme [dark|light]       choose theme
clear                    clear terminal view
history                  show this session history
whoami                   explain portfolio identity
date                     browser local date/time
status                   show content source / sync freshness
Unknown command response: "Command not supported in portfolio mode. Type help to see available commands." Never
invent output for ls, dir, ping, python, git, npm or other native OS commands. The web terminal is a deliberate portfolio
interface, not an OS shell.
Optional shortcuts: tab completion for registered commands, Up/Down history, Ctrl+L clear, clickable safe URLs, theme
toggle, reduced-motion preference, focus restoration and command suggestions. Escape and Ctrl+C cancel a local pending
UI action; never imply a remote process was killed.
7. Portfolio pages and information architecture
 Home: hero, introduction, quick terminal launcher, featured projects, accessible non-terminal navigation.
 Terminal: resizable embedded terminal panel, command reference, keyboard-first workflow and responsive fallback.
 Projects: searchable cards, filters, detail routes, screenshots, repositories and live links.
 Skills: grouped technologies and honest proficiency indicators.
 Education and certificates: institution, dates, issuer, credentials and external links.
 Milestones / experience: timeline and outcomes.
 About / contact / resume: downloadable resume if configured, accessible contact methods, social links.
 Settings: theme, font size, reduced motion, terminal preferences, data-source status.
 404 / offline: useful recovery paths and cached public content where available.
8. Branding and legal fidelity
MYCMD must be its own product name and visual identity. Terminal conventions (monospace font, prompt, ANSI colors,
tabs, cursor) are general interaction patterns. Do not copy Windows logos, Microsoft branding, system artwork, proprietary
icons, exact trade dress, or falsely present the application as an official Microsoft or Linux terminal. Display shell names
truthfully where actually used. Use appropriately licensed fonts/icons and include attribution where required.
--- PAGE 6 ---
MYCMD 2.0 | Codex Implementation Blueprint
6
9. Repository structure
mycmd/
  README.md  pyproject.toml  uv.lock  .env.example  .gitignore
  docs/ SRS.pdf ARCHITECTURE.md API.md SECURITY.md RUNBOOK.md
  apps/portfolio/                 # React + TS + xterm.js
    src/commands/ src/components/ src/pages/ src/data/
  src/mycmd/cli/                  # Typer commands
  src/mycmd/gui/                  # desktop UI
  src/mycmd/terminal/             # shell adapters and lifecycle
  src/mycmd/core/                 # entities, validation, services
  src/mycmd/storage/              # SQLite + migrations
  src/mycmd/sync/                 # durable queue, conflict logic
  src/mycmd/api_client/           # HTTP client
  server/app/                     # FastAPI, auth, routers, services
  server/migrations/              # Alembic
  tests/unit/ tests/integration/ tests/e2e/
  scripts/ .github/workflows/
10. Shared data model
All domain records: id UUID, owner_id UUID, created_at UTC, updated_at UTC, version integer, deleted_at nullable UTC,
type-specific fields. Local records additionally track sync_status and last_server_version. Validate length, URL scheme,
enum, date ordering, unique constraints and nullable fields consistently in Python and API.
 users(id, email unique, password_hash, status, created_at)
 projects(id, owner_id, slug, title, description, status, technologies JSON, links JSON, started_at, finished_at, notes,
version, updated_at, deleted_at)
 skills(id, owner_id, name, category, level, notes, updated_at, version, deleted_at)
 education(id, owner_id, institution, program, status, started_at, ended_at, notes, version, deleted_at)
 certificates(id, owner_id, name, issuer, credential_id, credential_url, issued_at, expires_at, notes, version, deleted_at)
 milestones(id, owner_id, title, due_at, priority, status, completed_at, notes, version, deleted_at)
 operation_log(owner_id, operation_id unique per owner, entity_type, entity_id, response_json, committed_at)
 change_log(sequence BIGINT auto-increment, owner_id, entity_type, entity_id, version, changed_at, tombstone)
 local_outbox(operation_id, entity_type, entity_id, action, base_version, payload_json, state, attempts, next_retry_at,
last_error)
 local_sync_state(device_id, owner_id, last_cursor, last_success_at) and conflicts(id, entity, local_json, server_json, state)
11. REST API contract
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/me
GET    /api/v1/{projects|skills|education|certificates|milestones}
POST   /api/v1/{entity}
GET    /api/v1/{entity}/{id}
PATCH  /api/v1/{entity}/{id}
DELETE /api/v1/{entity}/{id}
POST   /api/v1/sync/push
GET    /api/v1/sync/pull?cursor=...&limit=100
GET    /health
GET    /api/v1/public/portfolio
Return structured JSON errors with code, message, field errors, request_id; 400 invalid request, 401 unauthenticated, 403
unauthorized, 404 absent/not owned, 409 conflict, 422 validation, 429 rate limit, 500 sanitized failure. Use stable pagination
and explicit API schema in OpenAPI.
--- PAGE 7 ---
MYCMD 2.0 | Codex Implementation Blueprint
7
12. Offline-first sync: precise algorithm
 Every local mutation atomically updates its SQLite record AND appends an outbox operation in one transaction. Never
acknowledge success if either write fails.
 Generate entity UUID and operation UUID once, persist before transmission; include base_version and device_id.
 Push pending operations in deterministic order. API transaction validates identity, ownership, base_version and
idempotency key; updates entity and change_log together.
 If operation ID was already committed, return stored prior result rather than applying twice.
 For accepted operations, atomically update local server version and mark outbox operation complete; if a crash happens
before acknowledgement, retry safely.
 For conflict, preserve server and local versions, freeze conflicting operation, and present keep-local / keep-server / manual
merge options. Keep-local requires explicit new version-based update.
 Pull changes ordered by monotonically increasing server change_log sequence, scoped by owner; cursor is last fully
applied sequence. Apply page and cursor in one SQLite transaction.
 Never overwrite local unsynced edits during pull; create conflict record instead.
 Soft deletes propagate as tombstones; define retention and require full rebootstrap when cursor falls behind retained
history.
 Retry transient failures with capped exponential backoff + jitter; never retry auth or validation failures indefinitely.
 Multiple devices use per-device cursors; device identity and auth identity must not be conflated.
 After logout, protect or purge cached personal data by explicit policy; do not show another user’s records.
13. Authentication and secrets
 Use Argon2id for password hashes if password login is implemented; enforce rate limits and secure account recovery
policy.
 Use short-lived access tokens and revocable refresh sessions; store desktop secrets in OS keychain/keyring, not plaintext
settings.
 Require TLS for remote API; reject invalid certificates. CORS must explicitly allow configured portfolio origins only.
 Never ship server credentials, DB passwords, private keys or admin tokens to browser or desktop clients.
 Public portfolio endpoint returns curated public data only; no private owner notes or sensitive records.
 Enforce owner_id from authenticated identity, never trust client-supplied owner_id for authorization.
 Validate external URLs; prevent javascript: and unsafe protocols; escape terminal output to prevent injection.
 Audit auth failures and sync errors without logging tokens, passwords or full sensitive payloads.
14. Real shell adapter implementation
The desktop terminal adapter exposes start(shell, cwd, env), write(bytes), resize(cols, rows), interrupt(), terminate(), wait(),
and async output event stream. On POSIX use a PTY with a session/process group and OS-native resize ioctl. On Windows
use ConPTY through a verified library; fall back to an explicit "unsupported on this configuration" error, never a fake shell.
Start shell as current user with a sanitized, documented environment. Shell execution is inherently powerful and must
require trusted local installation.
Do not attempt to parse shell pipelines or redirectors in Python: the real shell owns them. Do not emulate cd by running each
command in a new subprocess. Use bounded buffers and backpressure; ensure exit, resize, encoding and cancellation are
tested.
--- PAGE 8 ---
MYCMD 2.0 | Codex Implementation Blueprint
8
15. CLI command interface
mycmd --help
mycmd status
mycmd shell                       # optional local interactive shell
mycmd gui                         # launch desktop
mycmd projects list --status active
mycmd projects add
mycmd projects show <uuid>
mycmd projects edit <uuid>
mycmd projects archive <uuid>
mycmd projects delete <uuid>
mycmd skills list
mycmd education list
mycmd certificates list
mycmd milestones list
mycmd search <text>
mycmd sync [--dry-run]
mycmd conflicts list
mycmd conflicts resolve <id>
mycmd export --format json --output backup.json
mycmd import --input backup.json --dry-run
mycmd doctor
mycmd config show
The normal terminal remains the real OS shell. Running mycmd commands is real program execution; mycmd shell
explicitly opens the configured native shell rather than pretending to be one. Interactive prompts must have noninteractive
flags for CI.
16. GUI design and behavior
 Left navigation: Dashboard, Terminal, Projects, Skills, Education, Certificates, Milestones, Sync, Settings.
 Terminal tab: shell selector, new/close session, title, current directory, resize, copy/paste, font controls, clear, session
status.
 Forms: create/edit validation, keyboard navigation, confirmation on destructive actions, loading states and meaningful error
messages.
 Dashboard: total records, pending changes, last sync, conflict count, connectivity status; no fabricated metrics.
 Sync: explicit retry, progress, queue count, error details and conflict resolution screen.
 Support high-DPI Windows and Linux desktops; dark/light themes and accessible contrast.
17. Browser UI implementation
React/TypeScript application should use a reusable terminal controller: immutable command definitions, parser, command
executor, output renderer, history store and focus manager. Prefer xterm.js for terminal appearance; for small screens offer
a plain accessible command input and clickable command suggestions. Portfolio content can come from checked-in JSON
for static hosting; optional read-only public API may update content. Loading failure must fall back to bundled public data
with a visible stale-data indicator.
Provide a visible non-terminal site navigation so users who cannot use command interfaces can access every portfolio
page. Respect reduced motion, keyboard focus and screen reader labels.
18. Export, import and backups
Export schema includes schema_version, exported_at UTC, owner scope, records by entity type and checksum. Validate
JSON schema before import; dry-run reports additions, changes, conflicts and invalid entries. Restore into a separate test
database before production restore. Use atomic file writes and documented backup encryption/storage procedures. Never
export passwords, refresh tokens or server secrets.
--- PAGE 9 ---
MYCMD 2.0 | Codex Implementation Blueprint
9
19. Error-handling matrix
Failure
Required outcome
Offline
Local CRUD works, queue persists, status says offline
API 401
Stop sync, prompt re-auth, preserve queue
API 409
Preserve both copies, show conflict resolution
Network timeout
Retry safely; no duplicate mutation
Corrupt local DB
Show recovery guidance; never silently erase
Missing shell executable
Show selection/install guidance; no fake output
PTY dependency missing
Explain unsupported runtime, disable local terminal
Invalid portfolio command
Friendly help suggestion; no fabricated result
--- PAGE 10 ---
MYCMD 2.0 | Codex Implementation Blueprint
10
20. Performance and accessibility targets
 Cold-start CLI help target under 2 seconds on a typical development laptop; measure in CI or release testing.
 Local personal-scale list/search target under 250 ms for 10,000 records on test hardware; benchmark and document
results.
 Terminal output should stream incrementally, including stderr and long-running commands; bounded scrollback default
5,000 lines configurable.
 Responsive browser layout from 320 px width; no horizontal overflow in primary navigation.
 Keyboard-only access to core browser/desktop actions, labeled controls, visible focus, screen-reader-friendly alternatives.
 No command loss or silent queue deletion on restart; define reproducible durability tests.
21. Development phases: strict dependency order
Phase
Milestone
Completion evidence
0
Foundation
Repo, lockfiles, formatting, lint, CI,
README, test skeleton
1
Domain and SQLite
Schemas, validation, local CRUD,
migration and export tests
2
Native CLI
Typer commands, help, prompts,
status, local CRUD
3
Real terminal engine
PTY/ConPTY adapters, streaming,
resize, lifecycle, shell tests
4
Desktop GUI
Forms, dashboard, terminal view and
shared services
5
Portfolio web
React pages, restricted terminal
registry, responsive UX
6
API and MySQL
Auth, ownership, CRUD, Alembic,
public curated endpoint
7
Sync
Outbox, idempotency, cursors,
conflicts, tombstones
8
Hardening
Security review, failure injection,
backup and restore
9
Packaging
Windows and Kali installers,
clean-install tests
10
Deployment
HTTPS API, MySQL backups, static
portfolio hosting
Each phase ends with executable tests and a short status report. Do not proceed to dependent phases while the prior phase
has failing tests, unless the failure is explicitly tracked and the dependency is isolated.
--- PAGE 11 ---
MYCMD 2.0 | Codex Implementation Blueprint
11
22. Automated acceptance tests
 CLI: help, CRUD, search, import/export roundtrip, validation and exit codes.
 Terminal POSIX: run pwd, cd, echo, pipes, interactive input, Ctrl+C, resize, Unicode and exit.
 Terminal Windows: run CMD and PowerShell, persistent cd, output streaming, Ctrl+C, exit and resizing on actual Windows
runner.
 Desktop: launch, open terminal, run real command, edit record, close and reopen.
 Web: all allowlisted commands return expected data, unknown commands do not execute OS processes, keyboard history
and accessibility checks.
 API: unauthorized access denied, cross-owner access denied, validation errors and rate limits tested.
 Sync: offline restart, reconnect, duplicate push, network failure after server commit, concurrent edit conflict, tombstone
propagation and cursor replay.
 Recovery: invalid import, corrupted backup, DB migration rollback/forward and restoration rehearsal.
 Packaging: clean Windows/Kali machine or VM installs and launches without development dependencies.
--- PAGE 12 ---
MYCMD 2.0 | Codex Implementation Blueprint
12
23. Exact development commands (initial scaffolding)
Kali Linux
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
mkdir -p ~/Projects/MYCMD && cd ~/Projects/MYCMD
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# After pyproject.toml is created:
python -m pip install -e ".[dev]"
python -m pytest -q
mycmd --help
Windows PowerShell
mkdir MYCMD
cd MYCMD
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
# After pyproject.toml is created:
python -m pip install -e ".[dev]"
python -m pytest -q
mycmd --help
The installer commands assume a compatible Python version and a generated pyproject.toml with a dev extra. Codex must
implement and verify those files; they are not pre-existing. If PowerShell script execution policy blocks activation, document
the venv python.exe alternative instead of changing global security policy.
Local API development
docker compose up -d mysql
python -m alembic -c server/alembic.ini upgrade head
python -m uvicorn server.app.main:app --reload
# Separate terminal: run integration tests against test DB
These are target commands, contingent on Codex creating docker-compose.yml, Alembic configuration, test database and
environment template. Never describe a command as verified until it has been run successfully.
24. Configuration contract
MYCMD_API_URL=https://api.example.invalid
MYCMD_SYNC_ENABLED=false
MYCMD_DATA_DIR=                    # optional platform default
MYCMD_DEFAULT_SHELL=               # optional OS detected
DATABASE_URL=                      # server only, never in client
MYCMD_SECRET_KEY=                  # server only
MYCMD_PUBLIC_ORIGIN=               # server CORS allowlist
The .env.example contains placeholders only. Fail fast on invalid server configuration; client must remain usable offline
without API credentials. Document all environment variables and default values.
25. Security threat model and deployment
 Public browser is untrusted: no terminal-to-shell bridge, no shell WebSocket, no unrestricted command API.
 Desktop shell runs with the current local user privileges and can modify that user’s files; display this fact in documentation.
 Use static hosting for portfolio frontend and separate HTTPS API origin for private records.
 Public profile data must be explicitly published, never derived by exposing the private CRUD API directly.
 Production DB accessible only from API infrastructure where possible; backups encrypted and restore-tested.
--- PAGE 13 ---
MYCMD 2.0 | Codex Implementation Blueprint
13
 No third-party telemetry by default; redact personal data from error reports and logs.
 Use dependency vulnerability scans and pin verified versions; never silently bypass TLS.
--- PAGE 14 ---
MYCMD 2.0 | Codex Implementation Blueprint
14
26. Codex master implementation instruction — COPY THIS
ROLE: You are the senior engineer implementing MYCMD 2.0.
INPUT: This entire PDF is the binding specification.
GOAL: Deliver a working repository, not a visual-only prototype.
1. Inspect the repository and environment first; report existing files.
2. Create an implementation plan mapped to requirement IDs.
3. Implement phases 0-10 in order; prefer small tested increments.
4. Preserve original MYCMD personal data management functionality.
5. Build genuine LOCAL shell execution using PTY/ConPTY.
6. NEVER connect anonymous portfolio users to an OS shell.
7. Build restricted browser commands with honest unsupported responses.
8. Do not invent outputs, mock persistence or hardcode fake success.
9. Use real migrations, transaction boundaries and safe sync semantics.
10. Write unit, integration and E2E tests with reproducible fixtures.
11. Run lint, typecheck, tests, build and smoke checks when possible.
12. Fix failures; never hide them or mark skipped tests as passing.
13. Record unsupported platforms, missing credentials and blockers.
14. Do not commit secrets, generated credentials or personal records.
15. Supply setup, run, test, deploy and rollback documentation.
16. Finish with evidence: commands run, results, known limitations.
17. Ask for credentials/hosting only when needed for deployment.
18. No claim of perfect operation without target OS testing.
START: Analyze repository, propose phase 0 file tree and execute it.
Continue phase by phase until blocked, then report exact blocker.
27. Codex handoff / progress-report template
PHASE: <number and name>
FILES ADDED/CHANGED: <paths>
IMPLEMENTED: <requirement IDs>
COMMANDS EXECUTED: <exact commands>
TEST RESULTS: <pass/fail/skip counts>
MANUAL VERIFICATION: <OS, steps, observations>
SECURITY CHECKS: <findings>
OPEN BLOCKERS: <exact cause and next action>
NEXT PHASE: <scope>
28. Release gate / final checklist
 No mock terminal output presented as real system output.
 Local desktop shell tested on both Windows and Kali Linux.
 Public browser never executes arbitrary shell commands.
 All five data categories have working CRUD and validations.
 SQLite survives offline restarts and power-loss-style interruptions.
 MySQL/API ownership and token security are tested.
 Idempotent sync and conflict tests pass with two devices.
 Import/export and backup restore verified in a test environment.
 Responsive portfolio and keyboard accessibility verified.
 Clean installation, README and deployment instructions verified.
 Known limitations explicitly listed; no unsupported guarantee of zero bugs.
29. Source alignment and improvements
--- PAGE 15 ---
MYCMD 2.0 | Codex Implementation Blueprint
15
Original MYCMD v1.1 sections 1-16 retained in substance: personal command centre, five data entities, native CLI, desktop
GUI, SQLite/MySQL, FastAPI, auth, offline sync, backups, packaging and Kali development workflow. Added: explicit
three-surface model, true PTY/ConPTY requirements, safe browser command interface, portfolio sitemap, full error matrix,
testable release gates and Codex execution contract.
Engineering caveat: no written SRS can guarantee bug-free software. The specification instead requires measurable
behavior, automated verification, transparent failure handling and tested installation on each supported platform.