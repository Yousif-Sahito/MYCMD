"""Validated, non-secret desktop preferences with atomic persistence."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile


@dataclass
class Preferences:
    theme: str = "dark"
    font_size: int = 14
    scrollback: int = 5000
    shell: str = ""
    cwd: str = str(Path.home())

    def validate(self) -> None:
        if self.theme not in {"dark", "light"}:
            raise ValueError("Theme must be dark or light")
        if type(self.font_size) is not int or not 8 <= self.font_size <= 40:
            raise ValueError("Font size must be between 8 and 40")
        if type(self.scrollback) is not int or not 100 <= self.scrollback <= 100000:
            raise ValueError("Scrollback must be between 100 and 100000")
        if not isinstance(self.shell, str) or not isinstance(self.cwd, str):
            raise ValueError("Shell and working directory must be text")
        if not Path(self.cwd).is_dir():
            raise ValueError("Default working directory does not exist")

    @classmethod
    def load(cls, root: Path) -> "Preferences":
        path = root / "desktop.json"
        if not path.exists():
            return cls()
        result = cls(**json.loads(path.read_text(encoding="utf-8")))
        result.validate()
        return result

    def save(self, root: Path) -> None:
        self.validate()
        root.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=root, delete=False) as f:
                temporary = Path(f.name)
                json.dump(asdict(self), f)
                f.flush()
                os.fsync(f.fileno())
            temporary.replace(root / "desktop.json")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
