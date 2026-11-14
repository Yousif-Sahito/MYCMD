"""Shell discovery without invoking shell text through a command processor."""

import os
import shutil
import sys
from pathlib import Path

from mycmd.terminal.models import ShellNotFoundError, ShellSpec


def discover_shell(name: str | None = None) -> ShellSpec:
    requested = name or os.environ.get("MYCMD_DEFAULT_SHELL")
    if sys.platform == "win32":
        candidates = {
            "cmd": [os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")],
            "powershell": ["powershell.exe"],
            "pwsh": ["pwsh.exe"],
        }
        default = "powershell" if shutil.which("powershell.exe") else "cmd"
        key = (requested or default).casefold().removesuffix(".exe")
        if key not in candidates:
            raise ShellNotFoundError(f"Unsupported Windows shell selection: {requested}")
        for candidate in candidates[key]:
            resolved = shutil.which(candidate)
            if resolved:
                return ShellSpec(
                    resolved,
                    ("/D", "/Q") if key == "cmd" else ("-NoLogo", "-NoProfile", "-NoExit"),
                    key,
                )
    else:
        defaults = (
            [requested]
            if requested
            else [os.environ.get("SHELL"), "/bin/bash", "/bin/zsh", "/bin/sh"]
        )
        for candidate in defaults:
            if not candidate:
                continue
            resolved = shutil.which(candidate) if not Path(candidate).is_absolute() else candidate
            if resolved and Path(resolved).is_file():
                name = Path(resolved).name
                args = (
                    ("--noprofile", "--norc", "-i")
                    if name == "bash"
                    else ("-f", "-i")
                    if name == "zsh"
                    else ("-i",)
                )
                return ShellSpec(str(resolved), args, name)
    raise ShellNotFoundError(f"Shell executable not found: {requested or 'platform default'}")
