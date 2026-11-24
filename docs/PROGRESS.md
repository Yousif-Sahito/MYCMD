# Phase 6 — authenticated API implementation (in progress)

The server package under `server/app` now provides FastAPI health/public/auth/routes,
SQLAlchemy models/repositories, Alembic migration 001 and Docker MySQL infrastructure.
Argon2id, signed access tokens and hashed rotated refresh sessions are implemented.
Private entity routes enforce owner scope and optimistic versions.

Local verification:

- Ruff format/lint: passed.
- Strict mypy: passed for 40 source files.
- API tests: 6 passed; 2 real-MySQL tests skipped without a disposable URL.
- Full pytest suite: 81 passed, 7 skipped.
- Source and clean-installed-wheel API smoke: passed.
- sdist/wheel build: passed; wheel includes `src/mycmd` and `server`.

Exact-SHA Windows, Ubuntu, portfolio and MySQL CI passed in run
`45347902966` at SHA `6907b7a3c4264c2afca5fe78ea30af994a36f5f9`.
The MySQL job ran Alembic migration 001 and real MySQL/API tests successfully.

# Phase 5 — public portfolio implementation

Phase 5 source implementation is under `apps/portfolio`. The React/TypeScript
application includes public routes, project filtering/detail routes, curated public
data, an allowlisted terminal parser and registry, xterm.js presentation, mobile
fallback input, themes, reduced-motion preferences, 404/offline states and Playwright
visual coverage. The browser terminal has no local terminal, SQL or remote shell
execution path.

Local frontend evidence:

- Strict TypeScript typecheck: passed.
- ESLint: passed.
- Vitest unit/component tests: 15 passed.
- Production build: passed; TerminalPage is route-lazy-loaded.
- Playwright Chromium desktop/mobile: 8 passed.
- Vitest unit/component tests: 17 passed standalone.
- Public URL/data validation and terminal history/argument fixes: verified.
- Eight specialist review responsibilities completed; no unresolved CRITICAL or HIGH
  security findings.

Exact-SHA Windows and Ubuntu CI passed for both the Python and portfolio jobs in
run `45298690921` at code SHA `7e67adbf79c112b0e36ceb31d453e4e9666278dc`.

# Phase 3 — local terminal engine (verified)

The Phase 3 implementation and expanded real-shell tests are committed on `main`
at `34566dd14c51f9425fe746cac3a061b7287db474`. Windows and Ubuntu GitHub Actions
run [43615724564](https://github.com/Yousif-Sahito/MYCMD/actions/runs/43615724564)
passed both jobs. The user's pre-existing README and `.gitignore` edits remain
separate and are preserved.

Implemented a typed `TerminalSession` / `TerminalBackend` boundary, shell
discovery, bounded incremental byte events, lifecycle states, and native adapters:
PyWinpty ConPTY on Windows and a controlling POSIX PTY on Linux. Sessions keep a
real shell alive across commands, support initial cwd/environment, resize,
interrupt, exit status, and controlled shutdown. Windows shutdown uses a targeted
process-tree cleanup only after graceful exit times out. The Windows-only
`pywinpty>=3.1.2` dependency is locked with a platform marker. Existing MYCMD
application commands and SQLite architecture remain separate and unchanged.

Windows 10 local evidence: full suite **52 passed, 6 platform/optional-shell
tests skipped**. Windows CI reported **53 passed, 5 POSIX-only tests skipped**;
Ubuntu CI reported **52 passed, 6 skipped** (five Windows-only tests and optional
Zsh absent). This includes live CMD, Windows PowerShell and PowerShell 7; directory
listing; persistent directory/environment changes; pipes, redirection, Unicode,
ANSI/VT transport, dimensions, line editing, tab completion, arrow history, Ctrl+C,
Ctrl+D, exit status, abrupt exit, bounded large-output streaming, and process-tree
cleanup. Ruff format/lint, strict mypy (17 source files), offline lock verification,
dependency compatibility (27 packages), sdist/wheel build, wheel-content checks,
and clean installed-wheel CLI plus real CMD smoke passed. Ubuntu verifies the
POSIX backend; it does not claim Kali-specific validation. Zsh was unavailable on
the Ubuntu runner.

See [TERMINAL_ENGINE.md](TERMINAL_ENGINE.md) for the API, shell configuration,
stream behavior, cleanup rules, security boundary and developer verification.

# MYCMD 2.0 progress

## Current status — Phase 1 complete; Phase 2 underway (2026-11-14)

Phase 1 completed at commit `6d0128b7de0fe09b129e0a4093404ef956da03a5`.
GitHub Actions run [43579616402](https://github.com/Yousif-Sahito/MYCMD/actions/runs/43579616402)
concluded success. Both `python (windows-latest)` and `python (ubuntu-latest)` jobs
passed, including frozen lock, dependency check, Ruff, mypy, pytest, build and wheel
smoke. This run was verified previously; no repeat API request was needed.

Phase 2 verification update: `render` now declares `Iterable[Record]`; strict mypy
passes. Ruff format check and lint pass; pytest reports **42 passed**. `git diff
--check` passes (Git emitted only line-ending normalization warnings for existing
working files). Using the installed uv executable outside the restricted sandbox,
`uv lock --check --offline` resolved 26 packages and passed. `uv build --offline`
created both sdist and wheel from the sdist successfully.

Installed-wheel smoke subsequently passed in normal Windows CMD, as verified by the
user: a fresh Python 3.13.18 environment was created, 15 dependencies installed,
`mycmd.exe --help` printed plain borderless help, and `mycmd.exe status` listed all
five entity categories with zero pending operations. The user's CMD output was
summarized in their message rather than attached verbatim.

Final local checks run in this workspace: uv `pip check` checked 26 installed packages
and reported all compatible; uv `lock --check --offline` resolved 26 packages.
Ruff formatting (16 files), Ruff lint, strict mypy (10 source files), and pytest
(**42 passed, 0 failed**) passed. CLI smoke for root help, status, project help, and
list commands for all five entity groups exited successfully against a fresh workspace
database. `git diff --check` passed with line-ending normalization warnings only.
The isolated offline source and wheel build passed earlier in this task; after the final CLI error-path and regression-test changes, uv rebuilt both artifacts successfully and the extracted-wheel smoke passed. CI for Phase 2
has not run; prepare the changes for commit and Windows/Ubuntu CI, but do not call
Phase 2 complete until both CI jobs pass. No push was made.

Phase 2 CLI work is underway. The regression suite now checks Unicode border glyphs directly and verifies inaccessible database paths return concise plain-text errors without traceback panels. Typer `>=0.29.1` and Rich `>=15.0.0` are declared
in pyproject.toml and uv.lock. Existing README.md and .gitignore edits were present
before this task and are being preserved. CLI verification results will follow.

The user confirmed a successful isolated build in normal Windows CMD using Hatchling
1.33.0, producing `mycmd-2.0.0.dev0.tar.gz` and
`mycmd-2.0.0.dev0-py3-none-any.whl`. Both files were observed in dist.
This supersedes the earlier missing-backend blocker; the project venv does not need
hatchling installed because the build backend runs in isolation.

Review fixed consistent-snapshot exports under concurrent writes, chronological
backup timestamp validation (including tombstone consistency), strict optimistic
version inputs, and URL control-character rejection. Regression tests cover these
changes. Generated SQLite sidecars and interrupted-export temporary files are now
ignored alongside existing build/cache/test artifacts. No generated artifacts are
tracked, confirmed with git ls-files and git check-ignore.

Executed successfully against the reviewed implementation:

- `.venv\Scripts\python.exe -m ruff format --check src server tests scripts --no-cache`
- `.venv\Scripts\python.exe -m ruff check src server tests scripts --no-cache`
- `.venv\Scripts\python.exe -m mypy --cache-dir .tools\phase1-mypy`
- `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .tools\phase1-review-tests`: **32 passed, 0 failed, 0 skipped**.
- Installed absolute-path uv: `lock --check --offline`: resolved 15 packages;
  `pip check --python D:\project\.venv\Scripts\python.exe`: 15 compatible packages.
- Installed absolute-path uv: `build --offline --out-dir .tools\phase1-review-dist`:
  built the sdist and built the wheel from that sdist successfully.
- `.venv\Scripts\python.exe scripts\check_wheel.py .tools\phase1-review-dist\mycmd-2.0.0.dev0-py3-none-any.whl`:
  isolated wheel import, bundled SQL migration, CRUD, outbox and reopen smoke passed.
- Absolute-path Git: `diff --check` passed; generated artifacts are ignored.

The uv executable initially returned Access is denied in the sandbox. Approved
execution outside the sandbox succeeded. No Windows permissions were changed and
no project dependencies were reinstalled. Offline build used cached isolated build
dependencies. The initial review lint import-order failure was corrected.

Windows/Ubuntu CI now includes the wheel smoke check after its existing frozen-lock,
dependency, lint, typecheck, pytest and build gates. New Phase 1 CI jobs have NOT run:
no commit or push was made. Prior Phase 0 CI success remains user-confirmed evidence.
Phase 1 is locally verified and ready for commit/CI; remote CI remains pending.
Phase 2 has not started. No production, Kali, hardware power-loss, network sync or
encrypted-backup support is claimed by this milestone.


## Previous Phase 1 verification (build blocker now resolved)

Phase 0 completion is confirmed by the user: local verification and both Windows
and Ubuntu GitHub Actions jobs passed. Those CI results were not independently
rerun in this session. Earlier environment blockers below are historical.

Verified here: Git 2.56.1.windows.1 using `C:\Program Files\Git\cmd\git.exe`,
clean starting working tree, Python 3.13.12 using `.venv\Scripts\python.exe`,
and readable project documentation. Generated caches are excluded from discovery.
No permissions, installations, deletions of existing files, commits or pushes occurred.

Phase 1 implements shared five-entity validation, owner-scoped CRUD, UUIDs, UTC
metadata, optimistic local revisions, tombstones, schema version 1, SQLite WAL/FULL
transactions, durable device identity and ordered outbox operations. Record and
outbox writes are atomic. Export uses an owner-scoped checksummed JSON envelope
and atomic file replacement; import defaults to dry-run and refuses to overwrite
conflicting records. Import is all-or-nothing and resets server tracking on restore.
No network sync or server acknowledgment semantics are implemented (Phase 7).

Validation commands use the existing environment, without dependency installation:

```powershell
& .\.venv\Scripts\python.exe -m ruff format --check src server tests scripts --no-cache
& .\.venv\Scripts\python.exe -m ruff check src server tests scripts --no-cache
& .\.venv\Scripts\python.exe -m mypy --cache-dir .tools\phase1-mypy
& .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .tools\phase1-final-tests
& .\.venv\Scripts\python.exe -m build --no-isolation --outdir .tools\phase1-dist
```

Build attempt failed: `ModuleNotFoundError: No module named 'hatchling'` /
`Backend 'hatchling.build' is not available`. No dependencies were installed per
user instruction. Phase 1 cannot be declared complete until a real build and
artifact verification pass. New code has not run on Ubuntu/Kali or GitHub Actions.
Final executed verification: Ruff formatting passed (11 files), Ruff lint passed,
mypy passed (7 source files), pytest **25 passed, 0 failed, 0 skipped** in 0.95s,
and `git diff --check` passed. Tests cover all five CRUD lifecycles, owner isolation,
stale revisions, uniqueness, restart persistence, forced outbox rollback, abrupt
process-exit rollback, backup roundtrip/dry-run/conflicts/corruption/invalid-entry
atomicity, future/corrupt database refusal, and domain validation. Initial lint,
type and collection failures were fixed before this final run. Build remains failed
for the missing backend described above; no build success is claimed.


## Current status — Phase 0 started, incomplete (2026-11-14)

Initial workspace contained only `MYCMD_V2_Codex_Implementation_Blueprint.pdf` (56,962
bytes), no source repository, no `.git`, no AGENTS.md and no requested Markdown file.
Read all 15 PDF pages before writing application scaffolding. Extracted the page text
to `docs/MYCMD_V2_Codex_Implementation_Blueprint.md`, explicitly labelled as a transcription.
The original PDF is unchanged.

### Checklist

- [x] Inspect workspace and local tool availability.
- [x] Read full supplied specification, including phase and release gates.
- [x] Create requirement-mapped implementation plan and architecture/security notes.
- [x] Create specified source, server, portfolio and test directory boundaries.
- [x] Add Python packaging metadata and target Python 3.13.12.
- [x] Add Ruff/mypy/pytest configuration and Windows/Linux CI definition.
- [x] Add environment template, ignore rules, README and runbook/API plans.
- [x] Run dependency-free foundation tests: **3 passed, 0 failed, 0 skipped**.
- [x] Compile scaffold Python source successfully.
- [ ] Initialize Git repository: Git is unavailable in this shell.
- [ ] Resolve and commit `uv.lock`: uv is unavailable and installation failed.
- [ ] Install development dependencies and run pytest itself.
- [ ] Run Ruff format/lint, mypy, build and installed-package smoke checks.
- [ ] Execute CI on real Windows/Linux runners (workflow has not run).
- [ ] Complete Phase 0, then begin Phase 1.

### Environment and commands executed

PowerShell on Windows at `D:\project`. `git status --short` failed because Git was not
found. The PATH Python alias could not execute. No uv, npm or Docker command was found.
A bundled MySQL Python was located and successfully ran the checks using:

```powershell
$env:PYTHONHOME='C:\Program Files\MySQL\MySQL Workbench 8.0\swb\shell\lib\Python3.13'
@'
import os, runpy
h = os.add_dll_directory(r'C:\Program Files\MySQL\MySQL Workbench 8.0\swb\shell\bin')
runpy.run_path('scripts/check_foundation.py', run_name='__main__')
'@ | & 'C:\Program Files\MySQL\MySQL Workbench 8.0\swb\shell\lib\Python3.13\python.exe' -
```

This uses that bundled runtime without modifying its installation; it is an environment
workaround, not a supported application installation. On normal CPython, use
`python scripts/check_foundation.py` for the same limited check.

Using this interpreter and DLL setup, pip was invoked through `runpy.run_module` with:

```text
pip install --target .tools uv --disable-pip-version-check --retries 0 --timeout 10
pip --isolated install --index-url https://pypi.org/simple --target .tools uv --disable-pip-version-check --retries 0 --timeout 10
```

Both attempts exited 1: `Could not find a version that satisfies the requirement uv
(from versions: none)` / `No matching distribution found for uv`. The original attempt
did not establish the underlying restriction; the follow-up below identifies socket
access denial. No dependency lock has been fabricated.

### Test coverage and limits

The three tests check metadata/version consistency, empty secret defaults with sync
disabled, and client package configuration excluding server code. They do not validate
an actual built wheel or application features. Compilation is a syntax check only.
The extracted document contains all 15 page markers. No GUI, shell backend, browser,
API, database persistence, sync, packaging or deployment behavior has been implemented
or verified. The CI workflow intentionally requires a real frozen lock and currently
cannot pass. Ubuntu CI will not substitute for Kali acceptance testing.

### Open blockers and next action

External action is required: permit package-download connectivity and install usable
development tooling from a regular Windows PowerShell session after approving the
installation commands in PHASE0_RECOVERY.md. The current execution environment restricts
network access and system writes; it cannot perform those installations. Generate the
lock and pass all checks before advancing. Full evidence follows below.

## Follow-up diagnosis (2026-11-14)

### Environment verified

| Item | Actual result |
| --- | --- |
| OS | Windows 10 Pro 22H2, build 19045.6456, AMD64; registry and platform checks |
| Project | `D:\project` |
| Python | MySQL-bundled CPython 3.13.12, 64-bit; PATH Python is an inaccessible WindowsApps alias |
| Python package manager | pip 25.3 in MySQL's bundled runtime; uv not installed |
| OS package manager | WinGet alias found, but executing it fails: `The file cannot be accessed by the system` |
| Project environment | No `.venv`; disposable `.tools/probe-venv` failed its SSL smoke test |
| Git | No PATH command, no GitForWindows registry install path, no executable in checked standard locations or accessible program directories |

`Get-CimInstance Win32_OperatingSystem` failed with `Access denied` / HRESULT
`0x80041003`; registry and `[Environment]::OSVersion` supplied OS information instead.
Git checks included Program Files, Program Files (x86), Local Programs, Scoop's default
Git path and Codex packages. Some WindowsApps/protected directories were unreadable,
so this is not a claim to have searched every possible custom location.

### Dependency diagnosis

- pip configuration inspection found no index, proxy, certificate, platform or no-index
  override explaining the failure. The explicit isolated index was `https://pypi.org/simple`.
- With the required MySQL DLL directory added before importing SSL, OpenSSL 3.5.5 loaded.
  Direct HTTPS to PyPI and `pip --isolated index versions uv --index-url
  https://pypi.org/simple --disable-pip-version-check --retries 0 --timeout 10 -vv`
  failed at socket creation, before package metadata could be read:

  ```text
  [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
  Could not fetch URL https://pypi.org/simple/uv/: connection error
  ERROR: No matching distribution found for uv
  ```

- An initial urllib probe imported urllib before adding DLL search paths and reported
  `unknown url type: https`. Reordering imports fixed that probe setup and exposed the
  socket error above. Neither error was a certificate-validation failure.
- The declared `>=3.13,<3.14` constraint accepts 3.13.12. pip wheel tags include
  `cp313-cp313-win_amd64`, `cp313-abi3-win_amd64`, `cp313-none-win_amd64`.
  All five dev/build requirement strings parse. Actual version resolution remains
  unverified because the index is unreachable. No requirements were removed or weakened.
- Default pip/uv cache directories were absent. Accessible program directories contained
  bundled pip and test wheels, but no usable uv or required development-tool cache.
- A fresh no-pip venv probe under ignored `.tools/probe-venv` emitted binary DLL copy
  warnings from MySQL's nonstandard venv layout. Running that venv without PYTHONHOME
  exited 1 with `ImportError: DLL load failed while importing _ssl: The specified module
  could not be found.` Do not use it as the project environment.
- A direct dependency installation was attempted with pip through the working DLL-aware
  interpreter, using these arguments:

  ```text
  pip --isolated install --index-url https://pypi.org/simple --target .tools/phase0-deps "pytest>=8.3,<9" "ruff>=0.11,<1" "mypy>=1.15,<2" "build>=1.2,<2" "hatchling>=1.27,<2" --disable-pip-version-check --retries 0 --timeout 5 -v
  ```

  It exited 1: `Could not find a version that satisfies the requirement pytest<9,>=8.3
  (from versions: none)` / `No matching distribution found for pytest<9,>=8.3`.

### Checks actually attempted

Each tool was invoked as its module through the bundled interpreter with the documented
DLL setup. The diagnostic loop continued to collect all failures; its overall completion
is not a successful verification gate.

| Check | Result |
| --- | --- |
| Ruff format (`ruff format --check .`) | Exit 1: `ImportError: No module named ruff` |
| Ruff lint (`ruff check .`) | Exit 1: `ImportError: No module named ruff` |
| mypy | Exit 1: `ImportError: No module named mypy` |
| pytest (`pytest -q`) | Exit 1: `ImportError: No module named pytest`; no tests collected |
| Build (`build`) | Exit 1: `ImportError: No module named build`; no artifacts built |
| Dependency lock | Not generated; uv unavailable and PyPI socket access denied |
| Foundation stdlib checks | 3 passed, 0 failed, 0 skipped; compilation passed after configuration edits |

CI now runs `uv lock --check` before frozen sync, `uv pip check`, and explicitly retains
the dev extra for every tool. Ruff excludes `.tools` so diagnostic environments and
downloaded third-party sources are not treated as application code. These changes are
not claimed lint-verified. CI has not run.

Next commands and installation approval boundary are in [PHASE0_RECOVERY.md](PHASE0_RECOVERY.md).
No system installation, firewall change, TLS bypass, Git initialization or commit was
performed. Phase 0 remains incomplete and Phase 1 has not started.

### User-supplied uv executable: execution denied

The user confirmed uv is installed at
`C:\Users\LENOVO\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe`.
Earlier PATH/standard-location checks did not establish that uv was absent from the
computer. Do not reinstall it. Executing the exact requested PowerShell command:

```powershell
& "C:\Users\LENOVO\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe" venv --python 3.13 "D:\project\.venv"
```

exited 1 with `Program 'uv.exe' failed to run: Access is denied` and
`FullyQualifiedErrorId : NativeCommandFailed`. This execution environment cannot launch
that installed executable. No installation or permissions workaround was attempted.
The virtual environment's Python executable remains absent, so its version cannot be
verified and dependency setup cannot proceed. Phase 0 remains incomplete.

### Remaining implementation requirements

All TR-01–TR-08 and FR-01–FR-10 remain incomplete. Phases 1–10 are not started.
See IMPLEMENTATION_PLAN.md for their scope, tests and release checklist. Credentials
and hosting are not needed at this stage. No public shell endpoint exists.

## Phase 2 CI correction

Initial pushed Phase 2 commit `0edbe9790cc2f6e017784c8f7913648a42600136` triggered
Actions run 43584493799. Ubuntu failed at `uv sync --frozen --extra dev`: Hatchling
reported invalid TOML at line 1. Inspection confirmed PowerShell had added a UTF-8 BOM
to pyproject.toml. Removed the BOM and verified Python tomllib parses the file. Ruff
format/lint, strict mypy, 42 tests, offline lock, isolated sdist/wheel build, and
extracted-wheel smoke all pass after correction. The BOM correction and this evidence were committed as `a03ff4f055cec6ac63c96481a53fda447d295f6c`.
GitHub Actions run [43584677394](https://github.com/Yousif-Sahito/MYCMD/actions/runs/43584677394)
passed on both Windows and Ubuntu. Both jobs passed lock, sync, dependency checks,
Ruff format/lint, mypy, pytest, build and wheel smoke. This evidence applies to the
corrected commit. A final documentation-only follow-up will also be checked by CI. The final release
report will identify its run and commit.

Final source verification: commit `5097891c40691e93e39644a06adaa7d56e448fea`
passed workflow run [43584816259](https://github.com/Yousif-Sahito/MYCMD/actions/runs/43584816259).
Both `python (windows-latest)` and `python (ubuntu-latest)` passed lock, sync, dependency
compatibility, Ruff format/lint, strict mypy, pytest, package build and wheel smoke.
The docs-only follow-up remains to be verified by CI.
