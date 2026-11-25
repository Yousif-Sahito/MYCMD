# 2. Python and Code Quality Review

## Scope

This pass reviewed Python source in `src/mycmd`, `server/app`, `scripts`,
`tests`, `pyproject.toml` and the deployment helpers.

## Executed gates

- Ruff format check: 77 files already formatted
- Ruff lint: passed
- Strict mypy: 44 source files, no issues
- Full pytest: 100 passed, 11 skipped
- uv lock/audit: lock passed; 65 packages had no known vulnerability

## Verified strengths

- Strict mypy configuration covers source and server packages.
- Domain validation is shared by CLI, GUI and API code.
- SQLite mutations are owner-scoped and transaction-oriented.
- API and backup exceptions use explicit application-level structures.
- The release runner cannot silently count all-skipped pytest groups as pass.

## Findings

| ID | Severity | Finding | Evidence | Recommendation |
| --- | --- | --- | --- | --- |
| PY-1 | LOW | Eleven pytest cases are skip-marked for external or platform dependencies | 5 MySQL, 6 platform/PTY cases | Continue CI or dedicated infrastructure for these cases |
| PY-2 | LOW | Starlette TestClient emits a deprecation warning | Full pytest warning output | Track the dependency migration when a compatible replacement is available |
| PY-3 | LOW | Some progress documents contain superseded historical blockers | `docs/PROGRESS.md`, QA reports | Preserve as history but link to current phase reports |

## Fixes reviewed

The service row decoder now constructs `Record` positionally instead of copying
through a dictionary/dataclass conversion. Focused 10,000-record and deployment
tests passed in the repository.
