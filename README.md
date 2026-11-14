# MYCMD 2.0

Offline-first personal command centre: native Python CLI, local desktop GUI with a real
PTY/ConPTY shell, and a restricted public portfolio terminal.

**Status: Phase 0 in progress. No application features are implemented yet.**
See [progress](docs/PROGRESS.md) for executed checks and blockers and
[implementation plan](docs/IMPLEMENTATION_PLAN.md) for the gated delivery sequence.

## Specification

The supplied `MYCMD_V2_Codex_Implementation_Blueprint.pdf` is the source specification.
The requested Markdown original was absent. A page-labelled text extraction is retained
in `docs/MYCMD_V2_Codex_Implementation_Blueprint.md`; it is not an independently supplied
Markdown specification. All 15 PDF pages were read before application scaffolding.

## Development setup (target workflow, not yet verified)

Install CPython 3.13.12, Git and uv. Run `uv lock` once to generate the dependency lock,
then `uv sync --frozen --extra dev`. Commit the resolved lock after verifying it.
Run `uv run ruff format .`, `uv run ruff check .`, `uv run mypy`,
`uv run pytest -q` and `uv run python -m build`.
CI uses the frozen lock and will fail until the lock is supplied.

An alternative after creating a normal Python environment is
`python -m pip install -e ".[dev]"`. On Windows use `.venv\Scripts\python.exe`
directly if activation is blocked; do not change global execution policy.
No `mycmd` entry point is advertised until Phase 2 provides working commands.

Python 3.13.12 is the initial runtime target. Windows and Kali require separate tests;
Ubuntu CI does not establish Kali support. macOS is unverified.

## Security boundaries

The desktop shell will run with the current user's privileges and can change that user's
files. Shell startup must be explicit. The public portfolio must never connect to this
shell, dispatch arbitrary commands, or receive private notes or credentials.
See [architecture](docs/ARCHITECTURE.md) and [security](docs/SECURITY.md).

## Configuration

`.env.example` documents the configuration contract; no loader exists yet.
`MYCMD_API_URL` is an HTTPS endpoint (example is intentionally non-routable),
`MYCMD_SYNC_ENABLED` defaults to false, and blank `MYCMD_DATA_DIR` / `MYCMD_DEFAULT_SHELL`
will select platform defaults. `DATABASE_URL`, `MYCMD_SECRET_KEY`, and
`MYCMD_PUBLIC_ORIGIN` are server-only; server startup must validate them in Phase 6.

Deployment, migrations and installers are not available yet. Do not use this foundation
to store real personal records or expose a production service.
