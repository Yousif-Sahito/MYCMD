# MYCMD 2.0 progress

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
