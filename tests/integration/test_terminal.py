"""Integration tests against genuine platform shell processes."""

import asyncio
import csv
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mycmd.terminal import (
    SessionState,
    SessionStateError,
    ShellSpec,
    TerminalError,
    TerminalSession,
    discover_shell,
)
from mycmd.terminal.models import validate_dimensions


async def read_until(session: TerminalSession, marker: str, timeout: float = 8.0) -> str:
    async def collect() -> str:
        output = ""
        async for event in session.read_events():
            if event.error:
                raise AssertionError(event.error)
            if event.data:
                output += event.data.decode("utf-8", "replace")
                if marker in output:
                    return output
        raise AssertionError(f"Session exited before marker {marker!r}; output={output!r}")

    return await asyncio.wait_for(collect(), timeout)


def python_command(code: str) -> str:
    if os.name == "nt":
        return f'"{sys.executable}" -c "{code}"'
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"


def windows_process_is_running(pid: str) -> bool:
    tasklist = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "tasklist.exe"
    result = subprocess.run(
        [str(tasklist), "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        check=True,
        text=True,
    )
    return any(len(row) > 1 and row[1] == pid for row in csv.reader(result.stdout.splitlines()))


def test_dimensions_and_shell_discovery() -> None:
    with pytest.raises(ValueError):
        validate_dimensions(0, 24)
    with pytest.raises(ValueError):
        validate_dimensions(80, 501)
    assert Path(discover_shell().executable).is_file()


def test_invalid_working_directory_rejected(tmp_path: Path) -> None:
    with pytest.raises(TerminalError, match="Working directory"):
        TerminalSession(discover_shell(), tmp_path / "missing")


def test_missing_shell_fails_without_leaking_session(tmp_path: Path) -> None:
    session = TerminalSession(ShellSpec(str(tmp_path / "missing-shell")), tmp_path)
    with pytest.raises(TerminalError):
        session.start()
    assert session.state is SessionState.FAILED


def test_session_state_guards(tmp_path: Path) -> None:
    session = TerminalSession(discover_shell(), tmp_path)
    with pytest.raises(SessionStateError):
        session.write(b"echo invalid")
    session.terminate()
    assert session.state is SessionState.CLOSED
    session.terminate()


def test_large_output_is_streamed_through_bounded_events(tmp_path: Path) -> None:
    shell = discover_shell("cmd" if os.name == "nt" else "bash")
    session = TerminalSession(shell, tmp_path, output_chunks=4)
    session.start()
    assert session._events.maxsize == 4
    try:
        command = python_command("import sys; sys.stdout.write('X' * 200000); sys.stdout.flush()")
        newline = "\r\n" if os.name == "nt" else "\n"
        session.write(f"{command}{newline}".encode())

        async def read_large_output() -> int:
            count = 0
            async for event in session.read_events():
                if event.error:
                    raise AssertionError(event.error)
                count += event.data.count(b"X")
                if count >= 200000:
                    return count
            return count

        assert asyncio.run(asyncio.wait_for(read_large_output(), 12)) >= 200000
    finally:
        session.terminate()


@pytest.mark.skipif(os.name != "nt", reason="Requires real Windows ConPTY")
def test_cmd_persistence_pipe_unicode_resize_and_exit(tmp_path: Path) -> None:
    session = TerminalSession(
        discover_shell("cmd"), tmp_path, env={"MYCMD_INITIAL": "initial"}, columns=80, rows=24
    )
    session.start()
    try:
        session.write(f"cd /d {tmp_path}\r\n".encode())
        session.write(b"echo %MYCMD_INITIAL%\r\n")
        session.write(b"set A=MYCMD-\r\nset B=CD-MARK\r\necho %A%%B%\r\n")
        output = asyncio.run(read_until(session, "MYCMD-CD-MARK"))
        assert str(tmp_path).casefold() in output.casefold()
        assert "initial" in output
        assert "\x1b[" in output

        session.write(b"set B=INITIAL-SIZE\r\n")
        session.write(b'mode con | findstr /i "Columns Lines" & echo %A%%B%\r\n')
        initial_size = asyncio.run(read_until(session, "MYCMD-INITIAL-SIZE"))
        assert "80" in initial_size and "24" in initial_size

        session.write(b"set B=PIPE\r\necho %A%%B% | findstr %A%%B%\r\n")
        assert "MYCMD-PIPE" in asyncio.run(read_until(session, "MYCMD-PIPE"))

        unicode_command = python_command("print(chr(38634))")
        session.write(f"{unicode_command}\r\n".encode())
        assert chr(38634) in asyncio.run(read_until(session, chr(38634)))

        redirected = tmp_path / "cmd-redirect.txt"
        session.write(b"set B=REDIRECT-WINDOWS\r\n")
        session.write(f"echo %A%%B%>{redirected} & type {redirected}\r\n".encode())
        assert "MYCMD-REDIRECT-WINDOWS" in asyncio.run(
            read_until(session, "MYCMD-REDIRECT-WINDOWS")
        )
        assert redirected.read_text().strip() == "MYCMD-REDIRECT-WINDOWS"

        session.resize(100, 30)
        session.write(b"set B=RESIZED\r\n")
        session.write(b'mode con | findstr /i "Columns Lines" & echo %A%%B%\r\n')
        resized = asyncio.run(read_until(session, "MYCMD-RESIZED"))
        assert "100" in resized and "30" in resized

        session.write(b"exit 7\r\n")
        assert session.wait(8) == 7
        assert session.state is SessionState.EXITED
    finally:
        session.terminate()


@pytest.mark.skipif(os.name != "nt", reason="Requires real Windows ConPTY")
def test_cmd_streaming_interrupt_and_cleanup(tmp_path: Path) -> None:
    session = TerminalSession(discover_shell("cmd"), tmp_path)
    session.start()
    try:
        command = python_command(
            "import time; print('MYCMD-' + 'STREAM', flush=True); time.sleep(30)"
        )
        session.write(f"{command}\r\n".encode())
        assert "MYCMD-STREAM" in asyncio.run(read_until(session, "MYCMD-STREAM"))
        assert session.wait(0.1) is None
        session.resize(120, 40)
        session.interrupt()
        session.write(b"set A=MYCMD-\r\nset B=SURVIVED\r\n")
        session.write(b'mode con | findstr /i "Columns Lines" & echo %A%%B%\r\n')
        resized = asyncio.run(read_until(session, "MYCMD-SURVIVED"))
        assert "120" in resized and "40" in resized
    finally:
        session.terminate(timeout=5)
    assert session.state is SessionState.CLOSED
    assert session.exit_code is not None


@pytest.mark.skipif(os.name != "nt", reason="Requires real Windows ConPTY")
def test_conpty_termination_cleans_active_process_tree(tmp_path: Path) -> None:
    session = TerminalSession(discover_shell("cmd"), tmp_path)
    session.start()
    command = python_command(
        "import os, time; "
        "print('MYCMD-' + 'PID:' + str(os.getpid()) + ':' + 'END', flush=True); "
        "time.sleep(30)"
    )
    try:
        session.write(f"{command}\r\n".encode())
        output = asyncio.run(read_until(session, ":END"))
        child_pid = output.split("MYCMD-PID:", maxsplit=1)[1].split(":END", maxsplit=1)[0]
        session.terminate(timeout=1)
        assert session.state is SessionState.CLOSED
        assert session.exit_code is not None
        assert not windows_process_is_running(child_pid)
    finally:
        session.terminate(timeout=5)


@pytest.mark.skipif(os.name != "nt", reason="Requires real Windows ConPTY")
def test_windows_powershell_real_session(tmp_path: Path) -> None:
    session = TerminalSession(
        discover_shell("powershell"), tmp_path, env={"MYCMD_INITIAL": "initial"}
    )
    session.start()
    try:
        session.write(b"Write-Output ('MYCMD-' + 'PS-READY')\r\n")
        assert "MYCMD-PS-READY" in asyncio.run(read_until(session, "MYCMD-PS-READY"))
        session.write(b"Write-Output $env:MYCMD_INITIAL\r\n")
        assert "initial" in asyncio.run(read_until(session, "initial"))
        session.write(b"$env:MYCMD_SESSION_MARK='persisted'\r\n")
        session.write(b"Write-Output ('MYCMD-' + $env:MYCMD_SESSION_MARK)\r\n")
        assert "MYCMD-persisted" in asyncio.run(read_until(session, "MYCMD-persisted"))
        session.write(b"exit 0\r\n")
        assert session.wait(8) == 0
    finally:
        session.terminate()


@pytest.mark.skipif(os.name == "nt", reason="Requires genuine POSIX PTY")
def test_bash_real_pty_persistence_resize_signals_and_cleanup(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not installed")
    session = TerminalSession(discover_shell(bash), tmp_path, env={"MYCMD_INITIAL": "initial"})
    session.start()
    try:
        session.write(b"stty size; printf 'MYCMD-INITIAL-'; printf 'SIZE-END\\n'\n")
        initial_size = asyncio.run(read_until(session, "MYCMD-INITIAL-SIZE-END"))
        assert "24 80" in initial_size

        session.write(b"pwd; printf 'MYCMD-PWD-'; printf 'END\\n'\n")
        output = asyncio.run(read_until(session, "MYCMD-PWD-END"))
        assert str(tmp_path) in output

        session.write(b"cd /; export MYCMD_PERSIST=works; printf 'MYCMD-SET-'; printf 'END\\n'\n")
        asyncio.run(read_until(session, "MYCMD-SET-END"))
        session.write(
            b'printf \'%s %s %s\\n\' "$PWD" "$MYCMD_PERSIST" "$MYCMD_INITIAL"; '
            b"printf 'MYCMD-CHECK-'; printf 'END\\n'\n"
        )
        persisted = asyncio.run(read_until(session, "MYCMD-CHECK-END"))
        assert "/ works initial" in persisted

        session.write(
            b"printf 'pipe-data\\n' | tr 'p' 'P'; printf 'MYCMD-PIPE-'; printf 'END\\n'\n"
        )
        assert "PiPe-data" in asyncio.run(read_until(session, "MYCMD-PIPE-END"))

        target = tmp_path / "redirect.txt"
        command = (
            f"printf 'redirect-'; printf 'ok\\n' > '{target}'; cat '{target}'; "
            "printf 'MYCMD-REDIRECT-'; printf 'END\\n'\n"
        )
        session.write(command.encode())
        assert "redirect-ok" in asyncio.run(read_until(session, "MYCMD-REDIRECT-END"))
        assert target.read_text().strip() == "ok"

        session.write(
            b"printf 'unicode-'; printf '\\u96ea-\\u7d42\\n'; "
            b"printf 'MYCMD-UNICODE-'; printf 'END\\n'\n"
        )
        assert "unicode-" + chr(38634) + "-" + chr(0x7D42) in asyncio.run(
            read_until(session, "MYCMD-UNICODE-END")
        )

        session.resize(100, 32)
        session.write(b"stty size; printf 'MYCMD-SIZE-'; printf 'END\\n'\n")
        assert "32 100" in asyncio.run(read_until(session, "MYCMD-SIZE-END"))

        command = python_command(
            "import time; print('MYCMD-' + 'LONG-RUN', flush=True); time.sleep(30)"
        )
        session.write(f"{command}\n".encode())
        assert "MYCMD-LONG-RUN" in asyncio.run(read_until(session, "MYCMD-LONG-RUN"))
        assert session.wait(0.1) is None
        session.resize(130, 40)
        session.interrupt()
        session.write(b"stty size; printf 'MYCMD-AFTER-'; printf 'INTERRUPT\\n'\n")
        after_interrupt = asyncio.run(read_until(session, "MYCMD-AFTER-INTERRUPT"))
        assert "40 130" in after_interrupt
        session.write(b"exit 7\n")
        assert session.wait(8) == 7
    finally:
        session.terminate()


@pytest.mark.skipif(os.name == "nt", reason="Requires genuine POSIX PTY")
def test_posix_termination_cleans_foreground_child(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not installed")
    session = TerminalSession(discover_shell(bash), tmp_path)
    session.start()
    command = python_command(
        "import os, time; print('MYCMD-' + 'PID:' + str(os.getpid()) + ':' + 'END', "
        "flush=True); time.sleep(30)"
    )
    try:
        session.write(f"{command}\n".encode())
        output = asyncio.run(read_until(session, ":END"))
        child_pid = int(output.split("MYCMD-PID:", maxsplit=1)[1].split(":END", maxsplit=1)[0])
        session.terminate(timeout=1)
        assert session.state is SessionState.CLOSED

        def child_exists() -> bool:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                return False
            return True

        deadline = time.monotonic() + 3
        while child_exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not child_exists(), f"Foreground process {child_pid} survived PTY shutdown"
    finally:
        session.terminate(timeout=5)
