"""Shared local client configuration; no GUI or CLI dependencies."""

import os
import sys
from pathlib import Path


def data_directory() -> Path:
    configured = os.environ.get("MYCMD_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "MYCMD"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "MYCMD"
    base = os.environ.get("XDG_DATA_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".local" / "share") / "mycmd"


def owner_id() -> str:
    return os.environ.get("MYCMD_OWNER_ID", "00000000-0000-4000-8000-000000000001")
