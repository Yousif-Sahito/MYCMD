# Phase 0 recovery commands

**Latest correction:** uv is already installed. Do not run the uv installation command
below; it is superseded. The supplied executable at
`C:\Users\LENOVO\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe`
failed to launch here with `Access is denied`. Run the user's exact venv command and
Python version check in regular PowerShell, or enable executable access for this
environment. No venv or dependencies have been created by that failed command.

These commands are proposed next steps, not successful execution evidence.
Run them in a regular Windows PowerShell session outside the restricted agent environment.
Stop on any error and retain its full output. Do not disable TLS checks or the firewall.

## Installation requires user approval

No system-level changes have been made. Approve installing Git and uv before running:

```powershell
winget install --id Git.Git -e --source winget
winget install --id astral-sh.uv -e --source winget
```

These commands are documented by [Git](https://git-scm.com/install/win) and
[uv](https://docs.astral.sh/uv/getting-started/installation/). If WinGet also reports
`The file cannot be accessed by the system` outside this session, use the official
installation pages; do not assume the alias is a functioning package manager.
If Git is already installed in a custom location, provide its absolute executable path
instead of installing another copy.

Open a new PowerShell window after installation, then verify:

```powershell
Set-Location D:\project
git --version
uv --version
Invoke-WebRequest -UseBasicParsing -Uri https://pypi.org/simple/pytest/ -TimeoutSec 15
```

The PyPI response must succeed over HTTPS. If it reports socket denial outside the agent
as well, the machine/network access policy needs investigation by its administrator.
If it succeeds outside but still fails inside the agent, the execution environment must
allow required package-download access, or setup/checks must run in the regular shell.

## Create the actual project environment and lock

Do not reuse `.tools/probe-venv` or set PYTHONHOME to MySQL's installation.
Use [uv-managed Python](https://docs.astral.sh/uv/guides/install-python/) for the pinned
version. Its download also requires network access. These commands install Python in
uv's user-managed storage and dependencies in the project environment:

```powershell
uv python install 3.13.12
uv venv --python 3.13.12 .venv
uv lock
uv lock --check
uv sync --frozen --extra dev
uv pip check
.\.venv\Scripts\python.exe -c "import sys, ssl, sqlite3; print(sys.version); print(sys.prefix); print(ssl.OPENSSL_VERSION); print(sqlite3.sqlite_version)"
```

Only a successful resolver may create `uv.lock`. Review it and retain the resolved
versions/hashes; never handwrite a guessed lock. See uv's
[locking documentation](https://docs.astral.sh/uv/concepts/projects/sync/).

## Mandatory verification

Run each command and stop on a nonzero exit. Fix reported errors and rerun the failed
checks; do not mark these complete just because the instructions exist.

```powershell
uv run --frozen --extra dev ruff format --check .
uv run --frozen --extra dev ruff check .
uv run --frozen --extra dev mypy
uv run --frozen --extra dev pytest -q
uv run --frozen --extra dev python -m build
```

If formatting fails, run `uv run --frozen --extra dev ruff format .` and rerun the check.
Inspect the built wheel and source archive. Test the wheel in a clean environment, with
isolated Python imports to prevent the working tree from concealing packaging mistakes:

```powershell
uv venv --python 3.13.12 .tools\wheel-smoke
uv pip install --python .tools\wheel-smoke\Scripts\python.exe .\dist\mycmd-2.0.0.dev0-py3-none-any.whl
.\.tools\wheel-smoke\Scripts\python.exe -I -c "import mycmd; assert mycmd.__version__ == '2.0.0.dev0'; print(mycmd.__file__)"
git init -b main
git status --short
```

Run the configured Windows and Linux CI jobs and retain their results. Do not claim that
local Windows checks establish Linux or Kali support. Update PROGRESS.md with exact
commands, exit statuses and test counts. Phase 0 remains incomplete until all mandatory
gates pass; Phase 1 must not start in the meantime.
