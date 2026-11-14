# MYCMD local terminal engine

Phase 3 provides the process backend for the later desktop terminal. It does not
add a desktop window, a remote shell, or shell execution to the public portfolio.
The terminal is a trusted local feature and runs with the current user's
permissions. It never elevates privileges or runs a configured startup script.

## Session API

`mycmd.terminal.TerminalSession` represents one long-lived native shell session.
Create it with a `ShellSpec`, optional initial directory and environment
overrides, and initial columns/rows. Then call `start`, `write(bytes)`,
`resize(columns, rows)`, `interrupt`, `read_events`, `wait`, and `terminate`.
The `TerminalBackend` protocol is the adapter boundary for platform PTYs.
Session states are `created`, `starting`, `running`, `stopping`, `exited`,
`failed`, and `closed`; invalid writes, resize, or interrupt calls raise
`SessionStateError`.

Output is delivered incrementally as `OutputEvent` byte chunks. On POSIX the
bytes come directly from the PTY. PyWinpty exposes decoded text, so the Windows
adapter encodes its output as UTF-8 at the adapter boundary. ANSI/VT sequences
are retained. A PTY combines stdout and stderr; the API intentionally makes no
claim to separate them. The event queue is bounded (128 chunks by default, with
4 KiB reads); if its consumer falls behind, the reader pauses and PTY backpressure
applies. A future UI should keep its display history separately in a bounded
5,000-line ring buffer, including its unfinished final line.

## Platform backends and shells

- Windows 10 1809 and later: `pywinpty` 3.x is required and the adapter requests
  its native ConPTY backend explicitly. CMD and Windows PowerShell are supported;
  PowerShell 7 (`pwsh`) is selectable when installed. Default selection is
  Windows PowerShell when found, then CMD. Shell aliases are `cmd`, `powershell`,
  and `pwsh`.
- POSIX: the standard-library `pty.fork` backend creates a controlling PTY and
  process group. Shell discovery tries `$SHELL`, then Bash, Zsh, and `/bin/sh`.
  Bash and Zsh are launched interactively without user profile files; `/bin/sh`
  is the fallback.
- `MYCMD_DEFAULT_SHELL` selects one of those platform shell names (or a PATH or
  absolute executable on POSIX). Unknown names and missing executables fail
  clearly. `TerminalSession` accepts initial environment overrides; changes made
  later inside the shell remain governed by the real shell process.
- `MYCMD_DATA_DIR` configures MYCMD application records. It does not configure
  the terminal's working directory or shell. Terminal sessions default to the
  current user's home directory unless a caller supplies `cwd`.

Resize updates the native PTY/ConPTY. Ctrl+C is sent as the terminal control
character; on POSIX the PTY's `ISIG` handling signals the foreground process.
Normal shutdown first sends Ctrl+C and the shell's `exit` command. If a Windows
shell and its foreground child do not stop, the last-resort cleanup targets that
ConPTY root PID and its descendants with `taskkill /T`; it does not target other
processes. POSIX shutdown sends SIGHUP to the session process group and escalates
to SIGKILL only after the configured timeout.

## Install and verify

```powershell
uv sync --frozen --extra dev
uv run --frozen --extra dev pytest -q
```

On Windows the locked runtime dependency installs PyWinpty. On Linux it is not
installed or imported. The platform integration tests launch real CMD and Windows
PowerShell or Bash processes; zsh coverage is conditional on zsh availability.
`scripts/check_installed_wheel.py` creates a clean environment, installs the
wheel, runs installed `mycmd --help` and `mycmd status`, and launches a real
installed-package shell session. CI runs those checks on Windows and Ubuntu.

The terminal backend is not exposed over HTTP or WebSocket. Terminal output must
be treated as untrusted text by a future renderer, not inserted as HTML. Ubuntu
CI verifies POSIX behavior; it does not claim Kali-specific validation. The
desktop GUI remains Phase 4, and the restricted public portfolio terminal remains
a separate Phase 5 component.
