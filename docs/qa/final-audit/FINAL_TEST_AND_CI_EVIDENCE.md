# Final Test and CI Evidence

## Local evidence

Executed in this audit:

- Python: 100 passed, 11 skipped
- Ruff formatting/lint: passed
- Strict mypy: passed
- uv audit: no known vulnerabilities in 65 packages
- Portfolio Vitest: 17 passed
- Portfolio Playwright: 8 passed
- Portfolio typecheck/lint/build: passed

## Local skips

- Five tests require `MYCMD_MYSQL_TEST_URL`
- PowerShell 7 was not installed
- Five POSIX PTY tests were excluded on Windows

## Exact-SHA CI evidence

Phase 10 implementation run:

- Run: https://github.com/Yousif-Sahito/MYCMD/actions/runs/45698439710
- Commit: `4373a70bb11eb153d38691f0c814ca85741357ed`
- Result: success
- Windows Python: passed
- Ubuntu Python: passed
- Windows portfolio: passed
- Ubuntu portfolio: passed
- MySQL migrations/API: passed
- Windows/Ubuntu packaged executable builds: passed

This audit added documentation and no source checksum can be claimed until the
next exact-SHA documentation commit is pushed and its Actions run passes.
