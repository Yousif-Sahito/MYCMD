# Phase 4 security review

Status: implemented trust boundary reviewed; release-wide dependency and CI gates pending.

Reviewer: independent delegated Codex architecture/security reviewer. Review
method: source inspection. No exploit or dependency vulnerability scan has yet
been executed by this reviewer.

## Files inspected

Complete approved blueprint, `docs/ARCHITECTURE.md`, `pyproject.toml`,
`.github/workflows/ci.yml`, `src/mycmd/core/models.py`,
`src/mycmd/core/service.py`, `src/mycmd/storage/database.py`,
`src/mycmd/cli/main.py`, `src/mycmd/terminal/{session,windows,posix,discovery,models}.py`,
and `tests/integration/test_terminal.py` at baseline
`2e5b7b4f175212740ef126d62dd3919b412fae51`.

## Existing boundaries observed

- Terminal adapters start local executables as the current user; no elevation or
  network listener is present in the inspected terminal modules.
- Shell discovery disables CMD AutoRun and PowerShell profiles; Bash/Zsh launch
  options disable their normal startup files. Shell semantics remain native.
- Services use parameterized SQL, owner scope, transactional outbox mutations and
  optimistic revision checks. URL validation permits HTTP(S), rejecting credentials
  and control characters. It does not automatically open links.
- Adapters inherit the current process environment and apply explicit overrides.
  This is local shell behavior, not secret isolation. Raw terminal input must not
  be logged or sent to remote telemetry by the GUI.

## Findings and required follow-up

| ID | Severity | Evidence / reproduction scope | Resolution |
| --- | --- | --- | --- |
| SEC-01 | INFORMATIONAL | GUI currently only `.gitkeep`; no WebEngine bridge exists | Origin, navigation, subresource, CSP, clipboard and bridge audit pending implementation |
| SEC-02 | MEDIUM | `WindowsBackend.terminate` returns when shell exits; `PosixBackend.terminate` signals shell process group. Existing tests cover ordinary active foreground children, not deliberately detached descendants or shell-exits-first cases | Verify normal GUI cleanup using real child PIDs. Document detached-process semantics separately; do not claim all descendant cleanup from existing tests |
| SEC-03 | INFORMATIONAL | Environment inheritance is implicit in both native backends | Document inherited environment and verify GUI never logs input or environment values |

## WebEngine release review checklist

The implemented view must load only bundled trusted content, constrain top-level
and subframe navigation, restrict external subresource/network requests, reject
popups, and expose only required input/resize operations through WebChannel.
Bridge access must not survive navigation to untrusted content. Shell output must
enter xterm as data, never interpolated executable HTML/JavaScript. OSC hyperlinks
and clipboard sequences need explicit safe handling. Local content must not gain
arbitrary filesystem or remote access. Do not disable WebEngine sandboxing or TLS
verification to make tests pass. Verify licenses, pinned renderer assets and
dependency security using actual tools.

## Verification and remaining issues

No production fixes applied. SEC-02 is an unverified coverage/lifecycle concern,
not a demonstrated exploit. No claim that dependencies are vulnerability-free.
Security acceptance remains open until resulting implementation, real cleanup
tests, bridge rejection tests and dependency checks are reviewed.

## Windows process-control baseline investigation

The lead delegated investigation of two baseline terminal failures. Reproduced
both in the restricted sandbox with the existing code:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_terminal.py::test_cmd_streaming_interrupt_and_cleanup tests/integration/test_terminal.py::test_conpty_termination_cleans_active_process_tree -q -p no:cacheprovider --basetemp .tools/phase4-terminal-review
```

Result: **2 failed in 43.22 s**. Ctrl+C did not produce the expected resumed-shell
output; process-tree termination timed out; retry cleanup also raised PyWinpty
`Element not found` from `cancel_io`.

Repeated identical test targets outside the sandbox using approved escalation,
with isolated `--basetemp .tools/phase4-terminal-review-unsandboxed`:
**2 passed in 1.92 s**. Then ran the complete existing terminal module outside
the sandbox with `--basetemp .tools/phase4-terminal-review-full`:
**10 passed, 6 skipped in 3.78 s**. Skips: PowerShell 7 absent, five POSIX-only
tests on Windows. CMD, Windows PowerShell, ordinary foreground-child cleanup,
interruption, Unicode, resizing and existing streaming tests passed.

Classification: reproducible execution-context restriction, not demonstrated
production regression. No backend code or test was weakened or changed. This
evidence validates the existing Windows engine baseline, not GUI integration,
detached children, Ubuntu or Kali. SEC-02's narrower coverage concern remains open.

## Resulting implementation review (2026-11-23)

Additional files inspected: all `src/mycmd/gui/*.py`, shared `config.py`,
`resources/terminal.html`, `terminal.js`, `terminal.css`, packaged renderer/license
filenames and lazy CLI launcher. Tests authored and run independently in
`tests/gui/test_security.py` using real Windows Qt WebEngine (PySide6 6.12.0).

Observed controls:

- Only exact local `terminal.html` is accepted for main navigation; frames are
  rejected. Request interception allows bundled-resource directory files and
  Qt's specific WebChannel script. No local HTTP listener or remote shell exists.
- CSP denies network connections, objects, frames and images; script sources are
  local and qrc. Popups, remote-content access and JavaScript clipboard APIs are
  disabled. Clipboard is exposed through explicit terminal copy/paste actions.
- Output uses base64 and xterm byte writes, not HTML interpolation. OSC link
  activation handler performs no external action. No input/environment logging,
  elevation, credentials or TLS bypass was found in the GUI source.
- Preferences contain only theme, font, scrollback, selected shell and directory,
  use validated atomic replacement and contain no authentication secret fields.
- Controller calls existing transactional services, preserving optimistic edits
  and owner scoping. Tests use temporary directories, never personal databases.

| ID | Severity | Finding | Resolution / evidence |
| --- | --- | --- | --- |
| SEC-01 | INFORMATIONAL | Initial bridge audit pending | Implemented local-origin restrictions independently tested; remote/data/arbitrary-local navigation, inline script injection, fetch and popup blocked |
| SEC-04 | HIGH | Shutdown originally ignored native termination failure | Lead fixed result propagation and session retention; injected failure/retry regression passed |
| SEC-05 | MEDIUM | Bridge accepted rows 501-1000 although backend maximum is 500 | Lead changed bound to 500; invalid-dimensions regression passed |
| SEC-06 | MEDIUM | Shared default WebEngine profile interceptor had lifecycle coupling | Lead added dedicated off-record profile; source reviewed and explicit isolation/off-record assertions passed |

Executed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/gui/test_security.py -q -p no:cacheprovider --basetemp .tools/phase4-security-review-final
```

Result: **6 passed in 3.70 s**, outside sandbox. The tests use actual renderer
navigation/CSP and shell-output transport; the cleanup failure is explicitly
injected and does not substitute for real process-cleanup testing. The dedicated
profile assertion was added afterward and awaits rerun. Ruff check and format
check pass for the authored test module.

Final expanded regression run (supersedes intermediate result above):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/gui/test_security.py -q -p no:cacheprovider --basetemp .tools/phase4-security-complete
```

**8 passed in 3.17 s**, actual Windows WebEngine outside sandbox. Dedicated
off-record profile isolation now passed. Added and passed attempted loading of
an arbitrary local JavaScript file outside the bundle (blocked, never executed).
Added application shutdown-failure injection verifying polling timers resume,
errors surface, the window stays open, and subsequent retry closes cleanly.
No unresolved HIGH or CRITICAL finding remains from this implemented GUI source
review. SEC-02 remains a documented boundary/coverage concern: deliberately
detached processes and shell-exits-first descendants are outside evidence from
the ordinary foreground-child cleanup tests, and require a release disposition.

Dependency vulnerability scanning and exact-SHA cross-platform CI remain release
gates; this reviewer has not executed a vulnerability scan. No claim of complete
security, unrestricted descendant termination, Ubuntu or Kali verification is made.
