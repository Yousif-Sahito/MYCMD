# Database and data-integrity review

Status: implementation reviewed; GUI test assertions pass, process exit remains a gate issue.

Reviewer: real delegated Codex agent `/root/data_quality`, acting independently
of the implementation coordinator. Initial inspection: 2026-11-22.

## Files inspected

- `src/mycmd/core/models.py`: fields, required values, enums, URL/date validation.
- `src/mycmd/core/service.py`: owner scope, CRUD, revisions, atomic outbox writes.
- `src/mycmd/core/backup.py`: snapshot export and conservative transactional import.
- `src/mycmd/storage/database.py` and `migrations/001_initial.sql`: connection,
  migration transaction, WAL/FULL durability, indexes and constraints.
- `src/mycmd/cli/main.py`: data path, owner configuration and service construction.
- `tests/integration/test_storage.py`, `test_cli.py`, `tests/unit/test_models.py`.

## Executed baseline evidence

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_models.py tests/integration/test_storage.py tests/integration/test_cli.py -q -p no:cacheprovider --basetemp .tools/data-review-baseline
```

Result: **39 passed in 8.34 seconds**, exit 0. Tests use isolated databases;
no personal database was opened or modified by this review.

Coverage includes five entity CRUD/reopen lifecycles, owner isolation, stale
revisions, atomic record/outbox rollback, duplicate project slug, invalid model
inputs, unsupported/corrupt database preservation, abrupt process rollback,
snapshot export with a concurrent writer, backup corruption/dry run/conflicts,
and CLI persistence and error handling. This is baseline service/CLI evidence,
not GUI interaction evidence.

## Findings and integration requirements

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| DATA-01 | INFORMATIONAL | SQLite connections enforce thread ownership. Worker jobs must create/use/close their own connection or use one persistent worker-owned connection. | Communicated to coordinator; verify implementation. |
| DATA-02 | INFORMATIONAL | Edits/deletes must submit the version originally displayed, not a newly fetched revision, to preserve conflict detection. | Communicated; verify GUI conflict regression. |
| DATA-03 | INFORMATIONAL | Optional blank dates/URLs should become `None`; empty strings fail shared validation. Completed milestone dates must be explicit and absent in other states. | Communicated; verify forms. |
| DATA-04 | INFORMATIONAL | CLI data path and owner configuration must be reused consistently by GUI. | Shared configuration extraction recommended; pending implementation. |

No existing service defect requiring production changes was established in this
baseline review. All GUI CRUD, GUI/CLI interoperability, GUI concurrent-edit,
restart and error-dialog acceptance remains NOT RUN until implementation exists.

## Fixes applied

None by this reviewer. Production files are read-only for this role.

## Implemented GUI review (2026-11-23)

Inspected `gui/controller.py`, `entities.py`, `forms.py`, `main_window.py`,
`settings.py`, `app.py`, shared `config.py`, and the terminal lifecycle portions.
The controller creates and closes SQLite connections inside its single worker;
widgets call service methods without SQL. Shared config preserves CLI data paths
and owner IDs. Edit and delete retain the displayed record version. Optional
blank date/URL fields become `None`; domain validation is reused. No migration
or schema change was introduced by GUI integration.

| Issue | Severity | Root cause / fix | Evidence |
| --- | --- | --- | --- |
| DATA-05 | HIGH | Comma-delimited list editing changed valid stored strings on unrelated saves. Coordinator replaced delimiter encoding with JSON array editing, preserving commas and embedded newlines. | `test_form_preserves_list_items_when_editing_notes`; comma case passed, expanded newline case requires final rerun. |
| DATA-06 | MEDIUM | Global failure signal reset all saving dialogs for unrelated failures. Coordinator introduced per-request error callbacks. | Inspected `Controller.submit/poll` and `RecordDialog.save`; stale and duplicate dialog regression assertions passed. |

Added independent real Qt tests in `tests/gui/test_data.py`. Five parameterized
tests exercise Create, View/Edit, Search, Filter, Delete confirmation and verify
actual SQLite tombstones/outbox operations. Additional tests exercise required
and date validation, CLI subprocess reads/edits of GUI-created data, window
restart, duplicate rejection, stale revision rejection and list preservation.

Executed outside sandbox with `QT_QPA_PLATFORM=offscreen`, isolated workspace
`.tools/data-review-gui3`: **8 passed in 12.41s**, but process exit **1** after
pytest summary. Diagnostic repeat `.tools/data-review-gui4`, `-s`: **8 passed in
8.13s**, process exit **1**, no subsequent diagnostic output. This is not a
successful overall gate. Qt/WebEngine teardown is under coordinator investigation.
Offscreen tests do not prove visible desktop appearance or Linux operation.

Initial test fixture teardown timed out because pytest-qt deletes registered
widgets before fixture finalizers; corrected the test to wait for asynchronous
shutdown through `before_close_func`. This was a test harness defect, not an
established production defect. Tests now close explicit inspection database
connections using `contextlib.closing`.
