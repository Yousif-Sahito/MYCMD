"""Typed terminal session contracts shared by platform adapters."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class SessionState(StrEnum):
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    EXITED = "exited"
    FAILED = "failed"
    CLOSED = "closed"


@dataclass(frozen=True)
class ShellSpec:
    executable: str
    args: tuple[str, ...] = ()
    name: str = "shell"


@dataclass(frozen=True)
class OutputEvent:
    session_id: str
    data: bytes = b""
    state: SessionState | None = None
    exit_code: int | None = None
    error: str | None = None


class TerminalError(RuntimeError):
    """Base error for terminal configuration and lifecycle failures."""


class ShellNotFoundError(TerminalError):
    """No usable shell executable was found."""


class UnsupportedTerminalError(TerminalError):
    """No genuine PTY backend is available on this runtime."""


class SessionStateError(TerminalError):
    """An operation is invalid for the current session state."""


class TerminalIOError(TerminalError):
    """A terminal input/output operation failed."""


def validate_dimensions(columns: int, rows: int) -> None:
    if (
        type(columns) is not int
        or type(rows) is not int
        or not 1 <= columns <= 1000
        or not 1 <= rows <= 500
    ):
        raise ValueError("Terminal dimensions must be columns 1-1000 and rows 1-500")


def validate_cwd(cwd: str | Path | None) -> Path:
    path = Path(cwd).expanduser() if cwd is not None else Path.home()
    if not path.exists() or not path.is_dir():
        raise TerminalError(f"Working directory does not exist or is not a directory: {path}")
    return path.resolve()
