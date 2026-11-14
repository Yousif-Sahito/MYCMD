# Phase 3 status — terminal engine in progress

The current work implements the shared terminal-session/backend protocol,
PyWinpty ConPTY on Windows, POSIX PTYs on Linux, shell discovery, byte-streamed
bounded events, resize, interrupt, lifecycle cleanup, and real-shell integration
tests. This is only the local backend; the desktop frontend remains Phase 4 and
the public portfolio command terminal remains Phase 5.

The implementation commit `8359508088852c11313ec79d502c13d26d7397ce` passed
Windows and Ubuntu Actions run [43612243867](https://github.com/Yousif-Sahito/MYCMD/actions/runs/43612243867).
That run reported 51 passed/2 POSIX-only skipped on Windows and 49 passed/4
Windows-only skipped on Ubuntu. The current worktree extends shell input and
repeated-session coverage; its Windows run reports **52 passed, 5 skipped**.
Ruff, strict mypy, offline lock validation, dependency compatibility,
sdist/wheel build, wheel-content checks, and clean installed-wheel CLI plus real
CMD smoke passed locally. The new test revision must pass both CI jobs before
closure. See [TERMINAL_ENGINE.md](TERMINAL_ENGINE.md).

# Implementation plan and requirement mapping

Each phase requires executable tests and a status report. Failures are fixed before
dependent work. Skips and unavailable target systems do not count as verification.

| Phase | Scope / requirement mapping | Exit evidence |
| --- | --- | --- |
| 0 | Foundation; sections 9, 21, 23, 24, 26 | Repository, real lockfiles, lint/format/typecheck, CI, build, foundation tests |
| 1 | Domain + SQLite; FR-01–05, FR-08, section 18 | Five entity schemas and CRUD, migrations, atomic outbox writes, restart durability, import/export roundtrip and invalid input tests |
| 2 | CLI; FR-06, FR-10 | Typer/Rich help, noninteractive flags and prompts, CRUD/search/status/config/doctor/export/import tests and real exit codes |
| 3 | Terminal; TR-01–04, TR-06 | Actual POSIX and Windows shell streaming, persistent cd, pipes, signals, resize, Unicode, backpressure and child cleanup tests |
| 4 | Desktop; TR-05, FR-07 | Shared CRUD forms/dashboard/settings/sync UI, Qt terminal bridge, launch/edit/reopen and real shell smoke tests |
| 5 | Portfolio; TR-07–08 | React pages and every section 6 command, safe parser/URLs/text output, unsupported OS commands, keyboard/mobile/accessibility/fallback tests |
| 6 | API + MySQL; FR-10, sections 10–13 | Alembic, real MySQL CRUD, auth/revocation/rate limits, cross-owner denial, public serialization, OpenAPI and structured errors |
| 7 | Sync; FR-09 | Two-device integration, duplicate push, lost acknowledgment, ordered cursor replay, conflicts, tombstones, offline restart and bounded retries |
| 8 | Hardening; FR-10, sections 18–20, 25 | Security review/scans, failure injection, backup/restore rehearsal, performance and accessibility measurements |
| 9 | Packaging; FR-10 | OS-specific PyInstaller artifacts and clean Windows/Kali installation/launch; no development dependency assumptions |
| 10 | Deployment; sections 25, 28 | HTTPS API, isolated MySQL, encrypted tested backups, static portfolio, rollback rehearsal and release checklist |

## Current milestone status

Phase 0 is complete per user-confirmed local verification and passing Windows and
Ubuntu CI jobs. Historical recovery instructions below are retained as an audit
trail, not active prerequisites. Do not reinstall tooling or repeat Phase 0.

Phase 1 is complete. CI run [43579616402](https://github.com/Yousif-Sahito/MYCMD/actions/runs/43579616402)
at commit `6d0128b7de0fe09b129e0a4093404ef956da03a5` completed successfully;
both `python (windows-latest)` and `python (ubuntu-latest)` passed all workflow steps.
Phase 1 is locally verified: shared domain validation, owner-scoped SQLite CRUD,
revision checks, tombstones, transactional migrations/outbox, restart and interrupted
transaction recovery, snapshot exports and validated atomic imports. Latest review:
32 tests passed; Ruff formatting/lint and mypy passed; offline lock check and installed
dependency check passed (15 packages); fresh isolated sdist/wheel build and extracted
wheel smoke passed. User's successful Hatchling 1.33.0 isolated build is also recorded
in PROGRESS.md. The previous build blocker is resolved.

CI now smoke-tests the wheel on Windows and Ubuntu after the existing verification
gates. Phase 1 commit and CI verification are complete. Phase 2 local verification is complete: 42 tests pass, Ruff formatting/lint and strict
mypy pass, uv dependency check and offline lock check pass (26 packages), isolated
sdist/wheel build passes, and installed-wheel CLI help/status passed in user-verified
Windows CMD on Python 3.13.18 with 15 dependencies. Current source CLI smoke also passes
for help/status and five entity list groups. Phase 2 is locally verified but cross-platform Actions exposed a UTF-8 BOM in
pyproject.toml. The BOM was removed and local checks rerun successfully; corrective commit `a03ff4f055cec6ac63c96481a53fda447d295f6c` passed GitHub Actions
run [43584677394](https://github.com/Yousif-Sahito/MYCMD/actions/runs/43584677394) on
Windows and Ubuntu. Both jobs passed all steps. A final docs-only commit is being checked separately by CI. The original Phase 2 commit is pushed; it is not complete until both Windows and
Ubuntu CI jobs pass. See PROGRESS.md for evidence. See DOMAIN_STORAGE.md for storage
decisions and limitations.

## Phase 0 tree

`pyproject.toml`, `.python-version`, `.env.example`, `.gitignore`, `README.md`,
`.github/workflows/ci.yml`, `docs/`, `src/mycmd/{cli,gui,terminal,core,storage,sync,api_client}`,
`server/{app,migrations}`, `apps/portfolio/src/{commands,components,pages,data}`,
`tests/{unit,integration,e2e}`, `scripts/`. Empty directories reserve boundaries only;
they do not represent implemented features. Add `uv.lock` only from a successful resolver.

## Historical Phase 0 recovery gate (superseded, 2026-11-14)

Latest correction: the user supplied the installed WinGet uv executable's exact path.
Launching it returned `Program 'uv.exe' failed to run: Access is denied` (exit 1).
Do not reinstall uv. The current blocker is executable access in this environment;
`.venv\Scripts\python.exe` remains absent. See PROGRESS.md for the exact command.

Status: **incomplete; Phase 1 blocked**. Follow-up diagnostics established Windows 10
Pro 22H2 / AMD64 at `D:\project`, bundled Python 3.13.12 and pip 25.3. Git was not
found in accessible standard installations. WinGet's alias cannot execute here.
Verbose pip and HTTPS checks exposed WinError 10013 socket denial, not a demonstrated
package-version conflict. The bundled Python's isolated venv also failed to load SSL.

- [x] Diagnose PATH, standard Git locations, package manager, Python tags and constraints.
- [x] Inspect indexes, available cache and HTTPS errors without disabling security checks.
- [x] Attempt dev dependency installation and all five verification commands; record failures.
- [x] Preserve every dependency constraint; add lock-consistency/dependency checks to CI.
- [ ] Resolve access to the existing uv executable; obtain approval if Git installation is needed.
- [ ] Restore package-download connectivity and provision a working Python 3.13.12 venv.
- [ ] Generate `uv.lock`, verify consistency, frozen-sync dev tools and pass `uv pip check`.
- [ ] Pass Ruff format/lint, mypy, pytest, build and clean installed-wheel smoke checks.
- [ ] Initialize the Git repository and execute Windows/Linux CI successfully.
- [ ] Record evidence and declare Phase 0 complete before domain/SQLite work.

Actual result: all five external tool checks exited 1 because their modules were missing;
no pytest cases ran and no build was produced. The three dependency-free foundation tests
still pass, but do not satisfy these missing gates. Exact errors and results are in
[PROGRESS.md](PROGRESS.md); approval-scoped next commands are in
[PHASE0_RECOVERY.md](PHASE0_RECOVERY.md).

## Release acceptance

- [ ] Real desktop shells verified on Windows and Kali; no simulated command output.
- [ ] Public terminal cannot execute native commands; accessible non-terminal navigation.
- [ ] Five categories support validated CRUD; offline restart and interrupted-write recovery.
- [ ] MySQL auth/ownership and two-device sync failure tests pass.
- [ ] Import/export, backup recovery and migration rollback/forward verified.
- [ ] Responsive/keyboard UI and startup/search performance measured.
- [ ] Clean installation and deployment/rollback documentation verified.
- [ ] All unsupported configurations and incomplete requirements recorded.
