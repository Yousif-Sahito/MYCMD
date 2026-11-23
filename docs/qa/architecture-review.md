# Phase 4 architecture review

Status: implementation reviewed; reported implementation defects corrected and regression-tested.

Reviewer: independent delegated Codex architecture/security reviewer. Production
files are read-only for this reviewer; fixes belong to the lead coordinator.

## Scope and method

Inspected the complete approved blueprint (15-page transcription),
`docs/ARCHITECTURE.md`, `pyproject.toml`, `src/mycmd/core/models.py`,
`src/mycmd/core/service.py`, `src/mycmd/storage/database.py`,
`src/mycmd/cli/main.py`, all terminal session/backend/discovery/model modules,
`tests/integration/test_terminal.py`, and `.github/workflows/ci.yml`.
Baseline commit: `2e5b7b4f175212740ef126d62dd3919b412fae51`.

## Decisions and required boundaries

- Existing architecture selects PySide6, locally bundled xterm.js and Qt WebEngine.
  Preserve Phase 3 `TerminalSession`; the GUI owns rendering and presentation.
- Core services and validation own all mutations. Widgets must not issue SQL or
  invoke CLI shell commands for CRUD.
- SQLite connections remain confined to their creating thread. A database worker
  must create and close its own connection; do not pass the CLI's connection to a
  Qt worker. Preserve optimistic `expected_version` on edits/deletes.
- Terminal start/terminate/write can block; Qt event handlers must enqueue work
  rather than call these operations synchronously. Worker results use queued
  signals; widgets are touched only by the GUI thread.
- CLI help must not import Qt/WebEngine. Shared configuration should sit below
  both CLI and GUI, rather than importing presentation code into another surface.
- Bounded engine events need bounded renderer delivery, including acknowledgement
  or another justified backpressure mechanism. An unbounded Qt signal queue would
  defeat Phase 3's bounded output guarantee.
- Shutdown must await worker and terminal cleanup before destroying Qt objects.

## Findings

| ID | Severity | Evidence | Disposition |
| --- | --- | --- | --- |
| ARCH-01 | INFORMATIONAL | GUI directory contains only `.gitkeep` at initial inspection | Implementation and resulting dependency/threading/lifecycle review pending |
| ARCH-02 | INFORMATIONAL | `database.connect` uses default thread affinity; `Service` retains `db` | Enforce connection ownership in GUI worker design; verify resulting code |
| ARCH-03 | INFORMATIONAL | `TerminalSession.start/terminate` perform native operations and joins | Require asynchronous Qt adapter and shutdown verification |

## Fixes and verification

No production fixes applied by this reviewer. No GUI functionality or independent
test execution claimed at this initial review. Circular dependencies, actual Qt
object ownership, renderer transport, and resulting maintainability will be
reviewed once implementation exists. Phase 4 architecture acceptance remains open.

## Resulting implementation review (2026-11-23)

Independently inspected `src/mycmd/config.py`, every GUI Python module,
`resources/terminal.html`, `terminal.js`, and `terminal.css`, and the lazy GUI
launcher integration in `src/mycmd/cli/main.py`.

The implemented dependency direction is sound: CLI and GUI import shared config,
domain and storage; domain/storage do not import either presentation surface.
`Controller.submit` creates/closes a connection inside one serialized worker.
GUI widgets use domain `validate`, `Service.create/update/delete/list/pending`;
there is no widget SQL. Dialogs preserve optimistic record versions. No schema
migration or parallel GUI persistence store was introduced.

`TerminalPage` uses the existing `TerminalSession`; output bytes are base64
transported and decoded into xterm's byte API. A bounded 64-event queue and
one-in-flight renderer acknowledgement preserve output backpressure. Native
operations run on an executor; polling and renderer signals run on the Qt thread.
Application close awaits a background cleanup future rather than blocking Qt.

| ID | Severity | Supporting code / finding | Fix and evidence |
| --- | --- | --- | --- |
| ARCH-04 | HIGH | Original `TerminalPage.shutdown` discarded termination Future, potentially closing window after failed native cleanup | Lead changed to `.result()` and retained session. `test_failed_session_close_retains_retry_handle` passed with injected native failure; failure propagates and retry succeeds |
| ARCH-05 | MEDIUM | `TerminalPage.shutdown` originally called Qt timer stop from shutdown worker | Lead removed worker-side timer access; `MainWindow.closeEvent` stops timers on GUI thread. Source verified |
| ARCH-06 | MEDIUM | Original close discarded session immediately and did not join reader before new session | Lead added close Future, retained session until success, joined reader, and cleared queued events after close. Failure/retry regression passed |
| ARCH-07 | MEDIUM | `MainWindow.finish_close` error branch reenables UI with controller/terminal timers stopped | Lead restarts both timers; `test_window_shutdown_failure_restores_polling_and_allows_retry` passed, verifying error propagation, resumed polling and successful subsequent close |
| ARCH-08 | MEDIUM | Initial renderer shared default WebEngine profile and global interceptor | Lead introduced per-view off-record profile; resulting source inspected, profile assertion passed |

The security test module executed **6 passed in 3.70 s** on actual Windows Qt
WebEngine outside the restricted sandbox. This includes negative lifecycle
failure injection, not real-shell cleanup evidence. Initial independent real
engine baseline was **10 passed, 6 skipped** (see security report). Full GUI
functional/end-to-end, large-list performance, cross-platform and visual checks
belong to their respective reports and are not inferred from this architecture
inspection. No production file was edited by this reviewer.

Final expanded review regression run:
`pytest tests/gui/test_security.py -q -p no:cacheprovider --basetemp .tools/phase4-security-complete`
using `.venv\Scripts\python.exe -m`, outside sandbox on Windows:
**8 passed in 3.17 s**. This supersedes the six-test intermediate result and
includes dedicated profile isolation, rejection of local scripts outside the
bundle, and application shutdown-failure recovery. Ruff lint and formatting pass
for this test module. Architecture review completion is not a release-wide pass;
the final report must still establish functional, packaging and cross-platform gates.
