"""Trusted local operating-system terminal engine."""

from mycmd.terminal.backend import TerminalBackend
from mycmd.terminal.discovery import discover_shell
from mycmd.terminal.models import (
    OutputEvent,
    SessionState,
    SessionStateError,
    ShellNotFoundError,
    ShellSpec,
    TerminalError,
    TerminalIOError,
    UnsupportedTerminalError,
)
from mycmd.terminal.session import TerminalSession

__all__ = [
    "OutputEvent",
    "SessionState",
    "SessionStateError",
    "ShellNotFoundError",
    "ShellSpec",
    "TerminalBackend",
    "TerminalError",
    "TerminalIOError",
    "TerminalSession",
    "UnsupportedTerminalError",
    "discover_shell",
]
