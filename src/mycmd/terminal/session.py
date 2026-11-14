"""Lifecycle-managed interactive shell session with bounded output events."""

import asyncio
import os
import queue
import sys
import threading
from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from uuid import uuid4

from mycmd.terminal.backend import TerminalBackend
from mycmd.terminal.models import (
    OutputEvent,
    SessionState,
    SessionStateError,
    ShellSpec,
    TerminalError,
    TerminalIOError,
    validate_cwd,
    validate_dimensions,
)


class TerminalSession:
    """One real PTY process. stdout/stderr share the PTY stream by design.

    The event queue is bounded. If the consumer falls behind, the PTY reader
    pauses and the operating system's PTY buffer applies backpressure.
    """

    def __init__(
        self,
        shell: ShellSpec,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        *,
        columns: int = 80,
        rows: int = 24,
        output_chunks: int = 128,
    ):
        validate_dimensions(columns, rows)
        if output_chunks < 1:
            raise ValueError("output_chunks must be positive")
        self.id = str(uuid4())
        self.shell = shell
        self.cwd = validate_cwd(cwd)
        self.env = dict(env or {})
        self.columns = columns
        self.rows = rows
        self.state = SessionState.CREATED
        self.exit_code: int | None = None
        self._events: queue.Queue[OutputEvent] = queue.Queue(output_chunks)
        self._stop = threading.Event()
        self._backend: TerminalBackend | None = None
        self._reader: threading.Thread | None = None
        self._waiter: threading.Thread | None = None
        self._state_lock = threading.RLock()

    def start(self) -> None:
        with self._state_lock:
            if self.state is not SessionState.CREATED:
                raise SessionStateError(f"Cannot start session in state {self.state}")
            self.state = SessionState.STARTING
        try:
            if sys.platform == "win32":
                from mycmd.terminal.windows import WindowsBackend

                self._backend = WindowsBackend(
                    self.shell, self.cwd, self.env, self.columns, self.rows
                )
            elif os.name == "posix":
                from mycmd.terminal.posix import PosixBackend

                self._backend = PosixBackend(
                    self.shell, self.cwd, self.env, self.columns, self.rows
                )
            else:
                raise TerminalError(f"Terminal backend is unsupported on {sys.platform}")
            self._backend.start()
        except Exception as exc:
            if self._backend is not None:
                try:
                    self._backend.terminate(0.5)
                    self._backend.close()
                except Exception:
                    pass
            with self._state_lock:
                self.state = SessionState.FAILED
            self._publish(OutputEvent(self.id, state=SessionState.FAILED, error=str(exc)))
            if isinstance(exc, TerminalError):
                raise
            raise TerminalError(f"Could not start {self.shell.name}: {exc}") from exc
        with self._state_lock:
            self.state = SessionState.RUNNING
        self._publish(OutputEvent(self.id, state=SessionState.RUNNING))
        self._reader = threading.Thread(
            target=self._read_loop, name=f"mycmd-pty-{self.id}", daemon=True
        )
        self._waiter = threading.Thread(
            target=self._wait_loop, name=f"mycmd-wait-{self.id}", daemon=True
        )
        self._reader.start()
        self._waiter.start()

    def _publish(self, event: OutputEvent) -> None:
        while not self._stop.is_set():
            try:
                self._events.put(event, timeout=0.1)
                return
            except queue.Full:
                continue

    def _read_loop(self) -> None:
        assert self._backend is not None
        try:
            while not self._stop.is_set():
                data = self._backend.read(4096)
                if not data:
                    if self._backend.exited:
                        break
                    continue
                self._publish(OutputEvent(self.id, data=data))
        except Exception as exc:
            if not self._stop.is_set():
                self._publish(OutputEvent(self.id, error=f"Terminal output failed: {exc}"))
        finally:
            self._backend.close_reader()

    def _wait_loop(self) -> None:
        assert self._backend is not None
        self.exit_code = self._backend.wait()
        reader = self._reader
        if reader is not None and reader is not threading.current_thread():
            reader.join(2.0)
        with self._state_lock:
            if self.state is not SessionState.CLOSED:
                self.state = SessionState.EXITED
        self._publish(OutputEvent(self.id, state=SessionState.EXITED, exit_code=self.exit_code))

    def write(self, data: bytes) -> None:
        if self.state is not SessionState.RUNNING or self._backend is None:
            raise SessionStateError(f"Cannot write in state {self.state}")
        if not isinstance(data, bytes):
            raise TypeError("Terminal input must be bytes")
        try:
            self._backend.write(data)
        except OSError as exc:
            raise TerminalIOError(f"Terminal input failed: {exc}") from exc

    def resize(self, columns: int, rows: int) -> None:
        validate_dimensions(columns, rows)
        if self.state is not SessionState.RUNNING or self._backend is None:
            raise SessionStateError(f"Cannot resize in state {self.state}")
        self._backend.resize(columns, rows)
        self.columns, self.rows = columns, rows

    def interrupt(self) -> None:
        if self.state is not SessionState.RUNNING or self._backend is None:
            raise SessionStateError(f"Cannot interrupt in state {self.state}")
        self._backend.interrupt()

    def terminate(self, timeout: float = 3.0) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        with self._state_lock:
            if self.state in {SessionState.CLOSED, SessionState.EXITED, SessionState.FAILED}:
                self.state = SessionState.CLOSED
                self._stop.set()
                backend = self._backend
                already_finished = True
            else:
                backend = self._backend
                already_finished = False
            if self.state is SessionState.CREATED:
                self.state = SessionState.CLOSED
                self._stop.set()
                return
            if not already_finished:
                self.state = SessionState.STOPPING
        if already_finished:
            for thread in (self._reader, self._waiter):
                if thread is not None and thread is not threading.current_thread():
                    thread.join(timeout)
            if backend is not None:
                backend.close()
            return
        assert backend is not None
        try:
            backend.terminate(timeout)
        except Exception:
            self._stop.set()
            for thread in (self._reader, self._waiter):
                if thread is not None and thread is not threading.current_thread():
                    thread.join(timeout)
            try:
                backend.close()
            except Exception:
                pass
            with self._state_lock:
                self.state = SessionState.FAILED
            raise
        else:
            self._stop.set()
            for thread in (self._reader, self._waiter):
                if thread is not None and thread is not threading.current_thread():
                    thread.join(timeout)
            backend.close()
            with self._state_lock:
                self.state = SessionState.CLOSED

    def wait(self, timeout: float | None = None) -> int | None:
        thread = self._waiter
        if thread is None:
            if self.state is SessionState.CREATED:
                raise SessionStateError("Session has not started")
            return self.exit_code
        thread.join(timeout)
        if thread.is_alive():
            return None
        return self.exit_code

    async def read_events(self) -> AsyncIterator[OutputEvent]:
        while not (
            self.state in {SessionState.EXITED, SessionState.CLOSED, SessionState.FAILED}
            and self._events.empty()
        ):
            try:
                event = await asyncio.to_thread(self._events.get, True, 0.1)
            except queue.Empty:
                continue
            yield event
            if event.state is SessionState.EXITED and self._events.empty():
                return
