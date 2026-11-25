# 3. Desktop and Terminal Review

## Scope

The pass reviewed `src/mycmd/terminal`, `src/mycmd/gui`, terminal tests,
PyInstaller configuration and CI packaging jobs.

## Verified evidence

- A typed `TerminalSession` protocol is implemented.
- Windows uses PyWinpty/ConPTY.
- POSIX uses `pty.fork`, controlling terminal and process groups.
- `TerminalPage` uses Qt worker futures and bounded event polling.
- Qt WebEngine navigation is constrained to bundled local resources.
- PyInstaller bundles the GUI and terminal renderer assets.
- Windows and Ubuntu CI built packaged GUI executables at the final Phase 9 run.

## Platform conclusion

| Platform | Evidence |
| --- | --- |
| Windows | Real local shell tests and exact-SHA CI packaging |
| Ubuntu | Real POSIX PTY tests and CI packaging |
| Kali | Not directly verified |
| macOS | Not implemented or verified |

## Findings

| ID | Severity | Finding | Evidence | Recommendation |
| --- | --- | --- | --- | --- |
| TERM-1 | MEDIUM | Detached descendants and shell-exits-first cleanup remain narrower coverage | Existing terminal lifecycle documentation | Add directed cleanup tests on Windows |
| TERM-2 | LOW | Direct Kali desktop verification is absent | No Kali runner or manual report | Add Kali to a controlled future packaging matrix |
| TERM-3 | LOW | Visible screen-reader and native DPI sessions are not a full accessibility certification | Existing GUI accessibility reports | Continue manual/automated assistive testing |

No fake terminal implementation or public shell bridge was found.
