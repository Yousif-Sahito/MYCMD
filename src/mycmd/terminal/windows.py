"""Windows native ConPTY adapter powered by pywinpty."""

import os
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from mycmd.terminal.models import ShellSpec, TerminalError, TerminalIOError


class WindowsBackend:
    def __init__(
        self, shell: ShellSpec, cwd: Path, env: Mapping[str, str], columns: int, rows: int
    ):
        self.shell, self.cwd, self.env = shell, cwd, dict(env)
        self.columns, self.rows = columns, rows
        self.pty: Any | None = None
        self.exited = False
        self._pending = bytearray()

    def start(self) -> None:
        try:
            from winpty import PTY, Backend  # type: ignore[import-untyped]
        except ImportError as exc:
            raise TerminalError("Windows ConPTY requires the installed pywinpty package") from exc
        try:
            self.pty = PTY(self.columns, self.rows, backend=Backend.ConPTY)
            cmdline = " " + subprocess.list2cmdline(list(self.shell.args))
            environment = os.environ.copy()
            environment.update(self.env)
            env_block = (
                "\0".join(
                    f"{key}={value}"
                    for key, value in sorted(
                        environment.items(), key=lambda item: item[0].casefold()
                    )
                )
                + "\0"
            )
            self.pty.spawn(self.shell.executable, cmdline=cmdline, cwd=str(self.cwd), env=env_block)
        except Exception as exc:
            raise TerminalError(
                f"Could not start ConPTY shell {self.shell.executable}: {exc}"
            ) from exc

    def read(self, size: int) -> bytes:
        if self.pty is None:
            return b""
        try:
            while not self._pending:
                chunk = self.pty.read(blocking=False)
                if chunk:
                    if isinstance(chunk, bytes):
                        self._pending.extend(chunk)
                    else:
                        # pywinpty exposes decoded Unicode; ConPTY VT bytes are
                        # transported as UTF-8 at this adapter boundary.
                        self._pending.extend(chunk.encode("utf-8", "surrogatepass"))
                    break
                if not self.isalive():
                    self.exited = True
                    return b""
                time.sleep(0.01)
            result = bytes(self._pending[:size])
            del self._pending[:size]
            return result
        except Exception:
            if not self.isalive():
                self.exited = True
                return b""
            raise

    def write(self, data: bytes) -> None:
        if self.pty is None:
            raise TerminalIOError("ConPTY is closed")
        try:
            self.pty.write(data.decode("utf-8", "strict"))
        except Exception as exc:
            raise TerminalIOError(f"ConPTY write failed: {exc}") from exc

    def resize(self, columns: int, rows: int) -> None:
        if self.pty is None:
            raise TerminalIOError("ConPTY is closed")
        self.pty.set_size(columns, rows)

    def interrupt(self) -> None:
        self.write(b"\x03")

    def isalive(self) -> bool:
        return self.pty is not None and bool(self.pty.isalive())

    def wait(self) -> int:
        while self.isalive():
            time.sleep(0.02)
        self.exited = True
        if self.pty is None:
            return 127
        status = self.pty.get_exitstatus()
        return int(status) if status is not None else 0

    def terminate(self, timeout: float) -> None:
        if self.pty is None or not self.isalive():
            self.exited = True
            return
        try:
            self.pty.write("\x03")
            time.sleep(0.1)
            self.pty.write("exit\r\n")
        except Exception:
            pass
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and self.isalive():
            time.sleep(0.02)
        if self.isalive():
            taskkill = (
                Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
            )
            try:
                subprocess.run(
                    [str(taskkill), "/PID", str(self.pty.pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                    timeout=max(1.0, timeout),
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise TerminalError(f"Could not stop the ConPTY process tree: {exc}") from exc
            self.pty.cancel_io()
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline and self.isalive():
                time.sleep(0.02)
            self.exited = not self.isalive()
            if not self.exited:
                raise TerminalError("ConPTY process tree did not stop before termination timeout")

    def close_reader(self) -> None:
        if self.pty is not None:
            try:
                self.pty.cancel_io()
            except Exception:
                if self.isalive():
                    raise

    def close(self) -> None:
        self.close_reader()
        self.pty = None
