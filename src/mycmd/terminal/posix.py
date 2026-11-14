"""Real POSIX controlling PTY backend."""

import errno
import fcntl
import os
import pty
import signal
import struct
import termios
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

from mycmd.terminal.models import ShellSpec, TerminalError, TerminalIOError


class PosixBackend:
    def __init__(
        self, shell: ShellSpec, cwd: Path, env: Mapping[str, str], columns: int, rows: int
    ):
        self.shell, self.cwd, self.env = shell, cwd, dict(env)
        self.columns, self.rows = columns, rows
        self.pid: int | None = None
        self.master: int | None = None
        self.exited = False
        self._status: int | None = None
        self._waited = threading.Event()

    def start(self) -> None:
        executable = Path(self.shell.executable)
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise TerminalError(
                f"Shell executable is missing or not executable: {self.shell.executable}"
            )
        fork = cast(Callable[[], tuple[int, int]], vars(pty)["fork"])
        pid, master = fork()
        if pid == 0:
            try:
                os.chdir(self.cwd)
                child_env = os.environ.copy()
                child_env.update(self.env)
                os.execvpe(
                    self.shell.executable, [self.shell.executable, *self.shell.args], child_env
                )
            except BaseException as exc:
                try:
                    os.write(1, f"MYCMD shell startup failed: {exc}\r\n".encode("utf-8", "replace"))
                finally:
                    os._exit(127)
        self.pid, self.master = pid, master
        self.resize(self.columns, self.rows)

    def read(self, size: int) -> bytes:
        if self.master is None:
            return b""
        try:
            return os.read(self.master, size)
        except OSError as exc:
            if exc.errno == errno.EIO:
                self.exited = True
                return b""
            raise

    def write(self, data: bytes) -> None:
        if self.master is None:
            raise TerminalIOError("PTY is closed")
        view = memoryview(data)
        while view:
            count = os.write(self.master, view)
            view = view[count:]

    def resize(self, columns: int, rows: int) -> None:
        if self.master is None:
            raise TerminalIOError("PTY is closed")
        ioctl = cast(Callable[[int, int, bytes], object], vars(fcntl)["ioctl"])
        ioctl(
            self.master,
            cast(int, vars(termios)["TIOCSWINSZ"]),
            struct.pack("HHHH", rows, columns, 0, 0),
        )
        if self.pid and not self.exited:
            try:
                killpg = cast(Callable[[int, int], None], vars(os)["killpg"])
                killpg(self.pid, cast(int, vars(signal)["SIGWINCH"]))
            except ProcessLookupError:
                pass

    def interrupt(self) -> None:
        if self.master is None:
            raise TerminalIOError("PTY is closed")
        self.write(b"\x03")

    def wait(self) -> int:
        if self.pid is None:
            return 127
        try:
            _, status = os.waitpid(self.pid, 0)
            self._status = os.waitstatus_to_exitcode(status)
            return self._status
        finally:
            self.exited = True
            self._waited.set()

    def terminate(self, timeout: float) -> None:
        if self.pid is None or self.exited:
            return
        try:
            killpg = cast(Callable[[int, int], None], vars(os)["killpg"])
            killpg(self.pid, cast(int, vars(signal)["SIGHUP"]))
        except ProcessLookupError:
            return
        if self._waited.wait(timeout):
            return
        try:
            killpg = cast(Callable[[int, int], None], vars(os)["killpg"])
            killpg(self.pid, cast(int, vars(signal)["SIGKILL"]))
        except ProcessLookupError:
            pass
        if not self._waited.wait(timeout):
            raise TerminalIOError("PTY process did not exit after SIGKILL")

    def close_reader(self) -> None:
        pass

    def close(self) -> None:
        if self.master is not None:
            os.close(self.master)
            self.master = None
