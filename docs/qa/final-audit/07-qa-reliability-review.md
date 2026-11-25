# 7. QA, Reliability and Recovery Review

## Scope

The pass reviewed unit/integration/GUI/E2E suites, release runner, failure
injection and backup/recovery evidence.

## Executed evidence

| Gate | Result |
| --- | --- |
| Python full suite | 100 passed, 11 skipped |
| Portfolio Vitest | 17 passed |
| Portfolio Playwright | 8 passed |
| Ruff format/lint | passed |
| strict mypy | passed |
| uv audit | 65 packages, no known vulnerabilities |
| production frontend build | passed |
| exact-SHA CI | current project reports and run history verified |

## Skips

- Five real-MySQL tests require `MYCMD_MYSQL_TEST_URL`
- PowerShell 7 was absent locally
- Five POSIX PTY tests were excluded on Windows

## Findings

| ID | Severity | Finding | Evidence | Recommendation |
| --- | --- | --- | --- | --- |
| QA-1 | MEDIUM | The local environment cannot execute disposable-MySQL backup/recovery semantics | 5 MySQL skips | Use MySQL CI or separately authorized disposable infrastructure |
| QA-2 | MEDIUM | Kali is not directly exercised | CI is Windows/Ubuntu | Add controlled Kali matrix if a supported installer target is required |
| QA-3 | LOW | Full-suite window can emit native crashes if unrelated processes interfere | Historical aggregate-run access violation | Isolated suite runs remain useful; preserve crash as CI/report evidence |
| QA-4 | LOW | Hardware power-loss testing is absent | Storage tests are process/transaction injections | Label simulations explicitly |
