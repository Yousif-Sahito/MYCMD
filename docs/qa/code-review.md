# Code-quality review

Status: resulting implementation reviewed; final tool/process gates pending.

Reviewer: real delegated Codex agent `/root/data_quality`. Initial baseline
inspection and tooling: 2026-11-22.

## Files inspected

`src/mycmd/core/{models,service,backup}.py`,
`src/mycmd/storage/database.py`, `src/mycmd/cli/main.py` (configuration and CRUD),
`tests/integration/test_storage.py`, `pyproject.toml`.

## Executed baseline tooling

| Command | Actual result |
| --- | --- |
| `.venv/Scripts/python.exe -m ruff check src server tests scripts --no-cache` | PASS, exit 0 |
| `.venv/Scripts/python.exe -m ruff format --check src server tests scripts --no-cache` | PASS, 25 files formatted, exit 0 |
| `.venv/Scripts/python.exe -m mypy --cache-dir .tools/data-review-mypy` | PASS, strict project configuration, 17 source files, exit 0 |
| Domain/storage/CLI pytest subset (see database review) | PASS, 39 tests, exit 0 |

These results precede Phase 4 source additions. They do not certify final source.
No test was removed and no type error was suppressed by this reviewer.

## Review findings

Baseline domain/service/storage separation supports GUI reuse. Transaction error
handlers rollback and re-raise; the broad exceptions inspected protect rollback
rather than manufacture successful results. The shared validator rejects unknown
fields and invalid types before persistence. Service revision checks are repeated
in the transactional UPDATE predicate, protecting against concurrent writes.

INFORMATIONAL: data-directory/owner configuration currently lives in CLI code;
extracting shared configuration avoids a GUI-to-CLI dependency. Coordinator was
notified. Resulting Qt signal/slot ownership, resource disposal, missing failure
paths, API compatibility, dead code and complexity must be reviewed after source
implementation. These are NOT RUN at baseline.

## Fixes and remaining issues

No production modifications made. Phase 4 review is not approved yet. See
`database-review.md` for integration concerns; final lint/type/test evidence must
be refreshed after implementation and fixes.

## Resulting implementation inspection (2026-11-23)

Inspected all GUI Python modules, shared `config.py`, and data GUI tests. Data
jobs own their connections and deliver callbacks on the Qt thread through a
timer. CLI imports remain free of Qt until GUI launch. The new configuration
module resolves the earlier GUI-to-CLI dependency concern. Widget SQL duplication
was not found. Validation and original-revision updates reuse domain services.

Concrete findings communicated to coordinator:

- HIGH DATA-05: delimiter-based array editing altered valid existing data.
  Coordinator replaced it with JSON array editing; independent regression added.
- MEDIUM DATA-06: globally broadcast data failures enabled unrelated saving
  dialogs. Per-request failure callbacks now scope each error correctly.
- INFORMATIONAL: Qt profile/page destruction order needs explicit verification;
  both were children of WebEngine view with profile created first. GUI test
  assertions passed but process exited 1; causation has not been established.

Executed strict mypy after implementation: **PASS, 26 source files**, exit 0.
Ruff observed an E501 in the concurrently edited `terminal.py:173` and formatting
changes needed in `test_navigation.py`; these were reported to coordinator and
require final rerun. Owned `test_data.py` lint/format passed. GUI subset produced
**8 passed** assertions but **exit 1** after summary; see database review. No
meaningful test was disabled or type error suppressed to obtain these results.

Remaining verification: clean process exit, final full Ruff/mypy/test suite,
packaging and platform CI. This report does not certify a final commit yet.
